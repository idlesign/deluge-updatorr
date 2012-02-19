import os
import logging
import pkg_resources
from datetime import datetime

import gtk
import deluge.component as component
import deluge.common
from deluge.ui.client import client
from deluge.ui.gtkui import notification
from deluge.plugins.pluginbase import GtkPluginBase
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall


log = logging.getLogger(__name__)


class UpdatorNotification(notification.Notification):

    _title = 'Deluge Updatorr'
    _message = ''

    def get_torrent_status(self, torrent_id=None):
        if torrent_id is not None:
            component.get('SessionProxy').get_torrent_status(torrent_id,
                ['name', 'num_files', 'total_payload_download']).addCallback(self._on_get_torrent_status)
        else:
            self._on_get_torrent_status({'total_payload_download': 'fake'})

    def _on_get_torrent_status(self, status):
        if status is None:
            return None
        if self.config['ntf_popup']:
            self.popup(status)

    def set_title(self, title):
        self._title = title

    def set_message(self, message):
        self._message = message

    def get_title(self):
        return self._enc(self._title)

    def get_message(self):
        return self._enc(self._message)

    def _enc(self, value):
        return deluge.common.xml_encode(value)

    def popup(self, status):
        if not deluge.common.windows_check():
            try:
                import pynotify
            except Exception:
                pass
            else:
                if not pynotify.init('Deluge'):
                    return None
                message = self.get_message()
                if 'name' in status:
                    message = '%s %s' % (message, self._enc('%s' % status['name']))
                self.note = pynotify.Notification(self.get_title(), message)
                self.note.show()


class GtkUI(GtkPluginBase):

    plugin_id = 'Updatorr'
    trackers_data_model = None
    status_bar_item = None

    def get_resource(self, name):
        """Returns resource from data dir."""
        return pkg_resources.resource_filename('updatorr', os.path.join('data', name))

    def enable(self):
        """Triggers when plugin is enabled."""
        self.glade = gtk.glade.XML(self.get_resource('config.glade'))

        self.tv_trackers = self.glade.get_widget('tv_tracker')
        self.ed_login = self.glade.get_widget('ed_login')
        self.ed_password = self.glade.get_widget('ed_password')

        component.get('Preferences').add_page(self.plugin_id, self.glade.get_widget('prefs_box'))
        pmanager = component.get('PluginManager')
        pmanager.register_hook('on_apply_prefs', self.on_apply_prefs)
        # TODO Cope with tv_tarckers repopulation on plugin reenable.
        pmanager.register_hook('on_show_prefs', self.on_show_prefs)
        self.add_context_menu_items()

        self.status_updator = LoopingCall(self.update_status_bar)
        self.status_updator.start(60)

        client.register_event_handler('UpdatorrUpdateDoneEvent', self.on_update_done_event)
        client.register_event_handler('UpdatorrErrorEvent', self.on_update_error_event)
        client.register_event_handler('UpdatorrUpdatesCheckStartedEvent', self.on_updates_started_event)
        client.register_event_handler('UpdatorrUpdatesCheckFinishedEvent', self.on_updates_finished_event)

    def update_status_bar(self):
        """Updates status bar item."""
        if self.status_bar_item is None:
            self.status_bar_item = component.get('StatusBar').add_item(stock=gtk.STOCK_REFRESH,
                text='', tooltip=_('Updatorr autoupdate status information'))
        client.updatorr.get_status().addCallback(self.get_status)

    DATE_FORMAT = '%b %d %H:%M'

    def get_status(self, status_data):
        """Returns autoupdate status and puts it our status bar item."""
        last_updated = datetime.fromtimestamp(status_data[0]).strftime(self.DATE_FORMAT)
        next_update = datetime.fromtimestamp(status_data[0] + (status_data[1] * 3600)).strftime(self.DATE_FORMAT)
        self.status_bar_item.set_text(_('last: %s, next: %s') % (last_updated, next_update))

    def disable(self):
        """Triggers when plugin is disabled."""
        self.status_updator.stop()
        component.get('StatusBar').remove_item(self.status_bar_item)
        self.status_bar_item = None
        self.remove_context_menu_items()
        self.trackers_data_model = None
        component.get('Preferences').remove_page(self.plugin_id)
        component.get('PluginManager').deregister_hook('on_apply_prefs', self.on_apply_prefs)
        component.get('PluginManager').deregister_hook('on_show_prefs', self.on_show_prefs)

    def init_tv_trackers(self):
        """Initializes trackers TreeView in preferences window."""

        # Initialize only once.
        if self.trackers_data_model is None:
            self.trackers_data_model = gtk.ListStore(str, bool, str, str)

            text_cell = gtk.CellRendererText()
            bool_cell = gtk.CellRendererToggle()

            tvc_domain = gtk.TreeViewColumn('Tracker domain', text_cell, text=0)
            tvc_login_req = gtk.TreeViewColumn('Login required', bool_cell)
            tvc_login_req.add_attribute(bool_cell, 'active', 1)
            tvc_login = gtk.TreeViewColumn('Login', text_cell, text=2)
            tvc_password = gtk.TreeViewColumn('Password', text_cell, text=3)
            tvc_password.set_visible(False)

            self.tv_trackers.append_column(tvc_domain)
            self.tv_trackers.append_column(tvc_login_req)
            self.tv_trackers.append_column(tvc_login)
            self.tv_trackers.append_column(tvc_password)

            self.tv_trackers.set_model(self.trackers_data_model)

            self.glade.signal_autoconnect({
                'on_btn_test_clicked': self.on_btn_test_clicked,
                'on_btn_apply_clicked': self.on_btn_apply_clicked,
                'on_tv_tracker_cursor_changed': self.on_tv_tracker_cursor_changed
            })

    def on_tv_tracker_cursor_changed(self, widget):
        """Triggered when trackers TreeView row is selected.
        Puts data from trackers TreeView into credentials Entry controls."""
        list_store, iter = self.tv_trackers.get_selection().get_selected()
        self.tv_current_domain = list_store.get_value(iter, 0)
        self.tv_current_login = list_store.get_value(iter, 2)
        self.tv_current_password = list_store.get_value(iter, 3)

        self.ed_login.set_text(self.tv_current_login)
        self.ed_password.set_text(self.tv_current_password)

    def on_btn_test_clicked(self, widget):
        """Triggers when test credentials button is pushed."""
        data = [self.tv_current_domain, self.ed_login.get_text(), self.ed_password.get_text()]
        client.updatorr.test_login(*data).addCallback(self.show_login_test_result)

    def show_login_test_result(self, success):
        """Shows credentials test result dialog."""
        if success:
            mtype = gtk.MESSAGE_INFO
            message = _('Credentials seem to be correct. Login was successful.')
        else:
            mtype = gtk.MESSAGE_ERROR
            message = _('Unable to login with given credentials.\nNote: some trackers may eventually activate capcha that Updatorr can not handle.')

        dialog = gtk.MessageDialog(flags=gtk.DIALOG_DESTROY_WITH_PARENT, type=mtype, buttons=gtk.BUTTONS_CLOSE, message_format=message)
        dialog.set_title(_('Tracker login test'))

        # Twisted might blow your away to hell eventually.
        result = Deferred()

        def response(dialog, resp):
            dialog.destroy()
            result.callback(resp)
            return False
        dialog.connect('response', response)
        dialog.show_all()
        return result

    def on_btn_apply_clicked(self, widget):
        """Triggers when apply credentials button is pushed.
        Puts data from credentials Entry controls into trackers TreeView.
        """
        # Get selected item for update.
        list_store, iter = self.tv_trackers.get_selection().get_selected()
        list_store.set_value(iter, 2, self.ed_login.get_text())
        list_store.set_value(iter, 3, self.ed_password.get_text())

    def on_update_done_event(self, torrent_id):
        """Triggers when torrent update is successful.
        Notifies user abount the event."""
        n = UpdatorNotification()
        n.set_title(_('Deluge Updatorr: torrent is updated'))
        n.notify(torrent_id)

    def on_update_error_event(self, torrent_id, error_text):
        """Triggers when torrent update failed.
        Notifies user abount the event."""
        n = UpdatorNotification()
        n.set_title(_('Deluge Updatorr Error'))
        n.set_message('%s at ' % error_text)
        n.notify(torrent_id)

    def on_updates_started_event(self):
        """Triggers when torrent update is started.
        Notifies user abount the event."""
        n = UpdatorNotification()
        n.set_message(_('Updates check is started'))
        n.notify(None)

    def on_updates_finished_event(self):
        """Triggers when torrent update is finished.
        Notifies user abount the event."""
        n = UpdatorNotification()
        n.set_message(_('Updates check is finished'))
        n.notify(None)

    # Context menu `toggle autoupdates` item states.
    CONTEXT_UPDATE_CHOICES = {
        True: _('Enable autoupdates'),
        False: _('Disable autoupdates')
    }

    # Context menu `check for updates` item states.
    CONTEXT_RUN_LABELS = {
        True: _('Check updates for selected'),
        False: _('Torrent updates in progress...'),
    }

    # Context menu `check scheduled updates` item states.
    CONTEXT_RUN_ALL_LABELS = {
        True: _('Check updates for scheduled'),
        False: CONTEXT_RUN_LABELS[False],
    }

    def add_context_menu_items(self):
        """Adds Updatorr items into torrents list context menu."""
        menu_bar = component.get('MenuBar')
        self.sep_1 = menu_bar.add_torrentmenu_separator()

        context_menu = menu_bar.torrentmenu
        self.cmenu_item_toggle = gtk.MenuItem(self.CONTEXT_UPDATE_CHOICES[True])
        self.cmenu_item_toggle.connect('activate', self.on_cmenu_item_toggle_activate)

        self.cmenu_item_run = gtk.MenuItem(self.CONTEXT_RUN_LABELS[True])
        self.cmenu_item_run.connect('activate', self.on_cmenu_item_run_activate)

        self.cmenu_item_run_all = gtk.MenuItem(self.CONTEXT_RUN_ALL_LABELS[True])
        self.cmenu_item_run_all.connect('activate', self.on_cmenu_item_run_all_activate)

        context_menu.connect('focus', self.on_cmenu_focus)
        context_menu.append(self.cmenu_item_toggle)
        context_menu.append(self.cmenu_item_run)
        self.sep_2 = menu_bar.add_torrentmenu_separator()
        context_menu.append(self.cmenu_item_run_all)

        self.cmenu_item_toggle.show()
        self.cmenu_item_run.show()
        self.cmenu_item_run_all.show()

    def remove_context_menu_items(self):
        """Removes Updatorr items from torrents list context menu."""
        context_menu = component.get('MenuBar').torrentmenu
        context_menu.remove(self.cmenu_item_toggle)
        context_menu.remove(self.cmenu_item_run)
        context_menu.remove(self.cmenu_item_run_all)
        context_menu.remove(self.sep_1)
        context_menu.remove(self.sep_2)

    def on_cmenu_focus(self, *args, **kwargs):
        """Triggered when torrents list context menu is summoned."""
        client.updatorr.get_items_to_update().addCallback(self.update_cmenu_item_toggle)
        client.updatorr.is_walking().addCallback(self.update_cmenu_item_run)

    def update_cmenu_item_run(self, is_walking):
        """Updates state for check for updates context menu items."""
        self.cmenu_item_run.set_label(self.CONTEXT_RUN_LABELS[not is_walking])
        self.cmenu_item_run_all.set_label(self.CONTEXT_RUN_ALL_LABELS[not is_walking])
        self.cmenu_item_run.set_sensitive(not is_walking)
        self.cmenu_item_run_all.set_sensitive(not is_walking)

    def update_cmenu_item_toggle(self, torrents_to_update):
        """Updates state for `toggle autoupdates` context menu item."""
        states = []
        for torrent_id in self.get_selected_torrents():
            state = torrent_id in torrents_to_update
            states.append(state)
        if states.count(True) >= states.count(False):
            self.cmenu_item_toggle.set_label(self.CONTEXT_UPDATE_CHOICES[False])
        else:
            self.cmenu_item_toggle.set_label(self.CONTEXT_UPDATE_CHOICES[True])

    def on_cmenu_item_toggle_activate(self, widget):
        """Triggered when `toggle autoupdates` context menu item is pushed."""
        enable = False
        if widget.get_label() == self.CONTEXT_UPDATE_CHOICES[True]:
            enable = True
        widget.set_label(self.CONTEXT_UPDATE_CHOICES[not enable])
        for torrent_id in self.get_selected_torrents():
            client.updatorr.set_items_to_update(torrent_id, enable)

    def on_cmenu_item_run_activate(self, widget):
        """Triggered when `check for updates` context menu item is pushed."""
        client.updatorr.run_walker(force=self.get_selected_torrents())

    def on_cmenu_item_run_all_activate(self, widget):
        """Triggered when `check scheduled updates` context menu item is pushed."""
        client.updatorr.run_walker(force=True)

    def get_selected_torrents(self):
        """Returns selected items from torrents list."""
        return component.get('TorrentView').get_selected_torrents()

    def on_apply_prefs(self):
        """Triggers when `apply preferences` button is pushed."""
        trackers_settings = {}

        for row in self.trackers_data_model:
            trackers_settings[row[0]] = {'login': row[2], 'password': row[3]}

        config = {
            'walk_period': self.glade.get_widget('walk_period').get_text(),
            'trackers_settings': trackers_settings
        }
        client.updatorr.set_config(config)

    def on_show_prefs(self):
        """Triggers on plugin preferences window show
        and after `apply preferences` button is pushed."""
        self.init_tv_trackers()
        client.updatorr.get_config().addCallback(self.config_to_ui)

    def config_to_ui(self, config):
        """Reads Updatorr configuration and puts data from it into
        preferences window UI controls."""
        self.glade.get_widget('walk_period').set_value(config['walk_period'])
        self.populate_tv_trackers(config['trackers_settings'])

    def populate_tv_trackers(self, settings):
        """Populates trackers TreeView with trackers data from Updatorr config."""
        self.trackers_data_model.clear()

        for domain, data in settings.items():
            self.trackers_data_model.append([domain, data['login_required'], data['login'], data['password']])

        # Select first tracker row.
        first_el_iter = self.trackers_data_model.get_iter_first()
        self.tv_trackers.get_selection().select_iter(first_el_iter)
        self.tv_trackers.emit('cursor_changed')
