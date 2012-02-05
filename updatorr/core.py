import os
import logging
import threading
import base64
import pkgutil
import time

import deluge.configmanager
import deluge.component as component
from deluge.common import is_url
from deluge.event import DelugeEvent
from deluge.core.rpcserver import export
from deluge.plugins.pluginbase import CorePluginBase
from twisted.internet.task import LoopingCall

# Line below is required to import tracker handler on fly.
import updatorr.tracker_handlers
from updatorr.utils import *


log = logging.getLogger(__name__)

# Import tracker handlers on fly.
# It is an .egg-friendly alternative to os.listdir() walking.
for mloader, pname, ispkg in pkgutil.iter_modules(updatorr.tracker_handlers.__path__):
    log.info('Updatorr Importing tracker handler file %s' % pname)
    __import__('updatorr.tracker_handlers.%s' % pname)


# Default plugin preferences.
DEFAULT_PREFS = {
    'last_walk': 0,
    'walk_period': 24,
    'trackers_settings': {},
    'torrents_to_update': []  # That might have been set(), except config serialization.
}


class UpdatorrUpdateDoneEvent(DelugeEvent):
    """This event fires up when a torrent is updated."""
    def __init__(self, torrent_id):
        self._args = [torrent_id]


class UpdatorrErrorEvent(DelugeEvent):
    """This event fires up when an error occures in tracker handler."""
    def __init__(self, torrent_id, error_text):
        self._args = [torrent_id, error_text]


class UpdatorrUpdatesCheckStartedEvent(DelugeEvent):
    """This event fires up when torrent updates check is started."""
    pass


class UpdatorrUpdatesCheckFinishedEvent(DelugeEvent):
    """This event fires up when torrent updates check is finished."""
    pass


class Core(CorePluginBase):

    walking = False
    plugin_id = 'Updatorr'

    def enable(self):
        """This one fires when plugin is enabled."""
        self.plugin = component.get('CorePluginManager')
        self.plugin.register_status_field(self.plugin_id, self.get_status_label)

        self.core = component.get('Core')
        self.torrents = self.core.torrentmanager.torrents

        self.config = deluge.configmanager.ConfigManager('updatorr.conf', DEFAULT_PREFS)
        self.torrents_to_update = self.config['torrents_to_update']
        self.walk_period = self.config['walk_period']
        self.last_walk = self.config['last_walk']
        self.trackers_settings = self.config['trackers_settings']

        self.update_trackers_settings()

        self.filter_manager = component.get('FilterManager')
        self.filter_manager.register_tree_field(self.plugin_id, self.get_filters_initial)

        # We will check whether it's time to go for updates every 60 seconds.
        self.walk_torrents_timer = LoopingCall(self.run_walker)
        self.walk_torrents_timer.start(60)


    def disable(self):
        """That one fires when plugin is disabled."""
        self.walk_torrents_timer.stop()
        self.filter_manager.deregister_tree_field(self.plugin_id)
        self.plugin.deregister_status_field(self.plugin_id)
        self.save_config()

    def update(self):
        """This one fires every second while plugin is enabled."""
        pass

    UPDATE_STATES = {True: 'On', False: 'Off'}

    def get_status_label(self, torrent_id):
        """This one is to update filter tree numbers.
        It is called every time torrent status is changed."""
        return self.UPDATE_STATES[self.check_is_to_update(torrent_id)]

    def get_filters_initial(self):
        """That are initial filter tree values."""
        return {'On': 0, 'Off': 0, 'All': len(self.torrents.keys())}

    def update_trackers_settings(self):
        """Returns registered handlers dictionary."""
        for domain, handler in get_registered_handlers().items():
            if domain not in self.trackers_settings:
                domain_dict = {
                    'login_required': handler.login_required,
                    'login': '',
                    'password': '',
                    'cookies': None
                }
                self.trackers_settings[domain] = domain_dict
            else:
                self.trackers_settings[domain].update({'login_required': handler.login_required})

    @export
    def get_status(self):
        """Returns tuple with Updatorr status data:
        last walk time, walk period in hours, is currently walking."""
        return self.last_walk, self.walk_period, self.walking

    @export
    def test_login(self, domain, login, password):
        """Launches login procedure for tracker domain.
        Returns True on success, overwise - False."""
        handler = get_tracker_handler({'comment': domain}, log)
        handler.set_settings(self.trackers_settings.get(domain))
        if handler is not None:
            return handler.login(login=login, password=password)
        return None

    @export
    def is_walking(self):
        """Returns boolean to identify whether update
        proccess is on the run."""
        return self.walking

    @export
    def run_walker(self, force=False):
        """Runs update process in a separate thread
        if it is a hight time for it and it's not already started."""
        if not force:
            now = time.time()
            next_walk = int(self.last_walk) + (int(self.walk_period) * 3600)
            log.debug('Updatorr run walker: walking=%s; next_walk=%s; now=%s' % (self.walking, next_walk, now))
            if self.walking:
                return False
            if next_walk > now:
                return False
        if force is True:
            force = []
        threading.Thread(target=self.walk, kwargs={'force': force}).start()
        return True

    def walk(self, force=False):
        """Implemets automatic torrent updates process.
        Automatic update is available for torrents selected by user
        and having tracker's page URL in torrent's `comment` field.

        Besides that torrent a tracker handler class should be
        associated with domain from the URL mentioned above.

        If `force` set to a list of torrent IDs, only those
        torrents will be checked for updates.
        If `force` is False every torrent scheduled to updates
        by used will be checked.

        """

        # To prevent possible concurent runs.
        self.walking = True

        log.info('Updatorr walking...')
        component.get('EventManager').emit(UpdatorrUpdatesCheckStartedEvent())

        allow_last_walk_update = False

        if force:
            torrents_list = force
        else:
            torrents_list = self.torrents_to_update

        for torrent_id in torrents_list:
            try:
                torrent_data = self.core.get_torrent_status(torrent_id, [])
            except KeyError:
                log.debug('Updatorr \tSKIPPED No torrent with id %s listed [yet]' % torrent_id)
                continue
            log.info('Updatorr Processing %s ...' % torrent_data['name'])
            if not is_url(torrent_data['comment']):
                log.info('Updatorr \tSKIPPED No URL found in torrent comment')
                continue
            # From now on we consider that update took its place.
            # If only this update is not forced.
            if not force:
                allow_last_walk_update = True
            tracker_handler = get_tracker_handler(torrent_data, log)
            if tracker_handler is None:
                self.dump_error(torrent_id, 'Unable to find retracker handler for %s' % torrent_data['comment'])
                continue
            tracker_handler.set_settings(self.trackers_settings.get(tracker_handler.tracker_host))
            new_torrent_filepath = tracker_handler.get_torrent_file()
            if new_torrent_filepath is None:
                self.dump_error(torrent_id, 'Error in tracker handling: %s' % tracker_handler.get_error_text())
                continue

            # Let's store cookies form that tracker to enter without logins in future sessions.
            self.trackers_settings[tracker_handler.tracker_host]['cookies'] = tracker_handler.get_cookies(as_dict=True)

            new_torrent_contents = read_torrent_file(new_torrent_filepath)
            new_torrent_info = read_torrent_info(new_torrent_contents)
            if torrent_data['hash'] == new_torrent_info['hash']:
                log.info('Updatorr \tSKIPPED Torrent is up-to-date')
                continue
            log.info('Updatorr \tTorrent update is available')

            new_torrent_prefs = get_new_prefs(torrent_data, new_torrent_info)
            added_torrent_id = self.core.add_torrent_file(None, base64.encodestring(new_torrent_contents), new_torrent_prefs)

            if added_torrent_id is not None:
                self.core.remove_torrent(torrent_id, False)
                log.info('Updatorr \tTorrent is updated')
                # Fire up update finished event.
                component.get('EventManager').emit(UpdatorrUpdateDoneEvent(new_torrent_info['hash']))
                # Add new torrent hash to continue autoupdates.
                self.set_items_to_update(new_torrent_info['hash'], True)
                # Remove old torrent from autoupdates list.
                self.set_items_to_update(torrent_id, False)
            else:
                self.dump_error(torrent_id, 'Unable to replace current torrent with a new one')

            # No littering, remove temporary .torrent file.
            os.remove(new_torrent_filepath)

        if allow_last_walk_update:
            # Remember lastrun time.
            self.last_walk = time.time()

        log.info('Updatorr walk is finished')
        component.get('EventManager').emit(UpdatorrUpdatesCheckFinishedEvent())
        self.walking = False

    def dump_error(self, torrent_id, text):
        """Logs error and fires error event."""
        log.info('Updatorr \tSKIPPED %s' % text)
        component.get('EventManager').emit(UpdatorrErrorEvent(torrent_id, text))

    @export
    def set_items_to_update(self, torrent_id, do_update):
        """Adds or removes given torrent to the `torrents-to-update list`."""
        if do_update:
            if torrent_id not in self.torrents_to_update:
                self.torrents_to_update.append(torrent_id)
        elif torrent_id in self.torrents_to_update:
            self.torrents_to_update.remove(torrent_id)
        self.save_config()

    @export
    def check_is_to_update(self, torrent_id):
        """Checks whether given torrent is set to update. Returns boolean."""
        return torrent_id in self.torrents_to_update

    @export
    def get_items_to_update(self):
        """Retunt a lis of to"""
        return self.torrents_to_update

    @export
    def set_config(self, config=None):
        """Sets the config dictionary of torrent IDs to update."""
        log.debug('Updatorr sets config')
        if config is not None:
            self.walk_period = config['walk_period']
            self.trackers_settings = config['trackers_settings']
        self.save_config()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        log.debug('Updatorr gets config')
        return self.config.config

    def save_config(self):
        """Dumps configuration file to file system ~/.config/deluge/updatorr.conf."""
        # Going through every name to be sure...
        self.update_trackers_settings()
        self.config['walk_period'] = int(self.walk_period)
        self.config['last_walk'] = int(self.last_walk)
        self.config['torrents_to_update'] = self.torrents_to_update
        self.config['trackers_settings'] = self.trackers_settings
        self.config.save()
