import os
import re
import tempfile
import urllib2

from urllib import urlencode
from updatorr.utils import Cookies


# This regex is used to get all hyperlinks from html.
RE_LINK = re.compile(r'href\s*=\s*"\s*([^"]+)\s*"[^>]*>', re.S | re.I | re.M)

# Cookie registry holds cookies from different tracker hosts.
COOKIES_REGISTRY = {}


class BaseTrackerHandler(object):
    """Base torrent tracker handler class offering
    helper methods for its ancestors."""

    # This tells Updatorr that login procedure is required.
    login_required = True

    # Torrent tracker host this handler is associated with.
    tracker_host = None
    # Torrent data from Deluge session.
    torrent_data = {}
    # Torrent hash from Deluge session data.
    torrent_hash = None
    # Resource URL from torrent comment.
    resource_url = None

    # Updatorr plugin logger instance.
    _log = None
    # Tracker specific settings (e.g. credentials).
    _tracker_settings = {}
    # Occured error description.
    _error_text = ''

    def __init__(self, tracker_host, torrent_data, logger):
        self.tracker_host = tracker_host
        self.torrent_data = torrent_data
        self._log = logger
        self.torrent_hash = torrent_data.get('hash')
        self.resource_url = torrent_data.get('comment')

    def set_settings(self, setting):
        """Stores tracker specific settings (e.g. credentials)
        for further usage."""
        if setting is None:
            setting = {}
        self._tracker_settings = setting
        # Initialize cookies data from previous handler session.
        if 'cookies' in setting:
            self.reset_cookies(setting['cookies'])

    def get_settings(self, field=None):
        """Returns tracker specific settings dictionary.
        Use `field` param to get definite settings value.
        """
        if field is None:
            return self._tracker_settings
        return self._tracker_settings.get(field)

    def login(self, login, password):
        """Tracker login procedure should be implemented
        in child class if necessary."""
        return False

    def get_error_text(self):
        """Returns handling error description if any."""
        return self._error_text

    def dump_error(self, text):
        """Stores handling error description for further usage."""
        self._error_text = text
        self.debug('Error: %s' % text)

    def get_resource(self, url, form_data=None):
        """Returns an HTTP resource data from given URL.
        If a dictionary is passed in `form_data` POST HTTP method
        would be used to pass data to resource (even if that dictionary is empty).

        """
        self.debug('Getting page at %s ...' % url)

        if form_data is not None:
            form_data = urlencode(form_data)

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.get_cookies()))
        request = urllib2.Request(url, form_data,
                                  {'User-agent': 'Mozilla/5.0 (Ubuntu; X11; Linux i686; rv:8.0) Gecko/20100'})

        try:
            response = opener.open(request)
        except urllib2.URLError:
            return {}, ''

        return response.info(), response.read()

    def store_tmp_torrent(self, file_contents):
        """Stores downloaded .torrent file contents
        in a temporary file within a filesystem.
        Returns a filepath to that file.

        """
        fd, fpath = tempfile.mkstemp()
        f = os.fdopen(fd, 'w')
        f.write(file_contents)
        f.close()
        return fpath

    def set_cookie(self, name, value):
        """Stores a single cookie into cookies registry
        for further usage.

        """
        self.get_cookies().add(name, value)

    def reset_cookies(self, cookies_dict):
        """Initializes cookies registry for current tracker
        with data from the given dictionary.

        """
        global COOKIES_REGISTRY
        COOKIES_REGISTRY[self.tracker_host] = Cookies(init_from_dict=cookies_dict)

    def get_cookies(self, as_dict=False):
        """Returns cookies for this tracker.
        If ``as_dict`` is True returns a dictionary with cookies data,
        otherwise return CookieJar object.

        """
        if self.tracker_host not in COOKIES_REGISTRY:
            COOKIES_REGISTRY[self.tracker_host] = Cookies()
        if as_dict:
            return COOKIES_REGISTRY[self.tracker_host].to_dict()
        return COOKIES_REGISTRY[self.tracker_host]

    def find_links(self, page_html):
        """Returns a list witj hyperlinks found in supplied html."""
        links = []
        for match in re.finditer(RE_LINK, page_html):
            links.append(match.group(1))
        return links

    def get_torrent_file(self):
        """This method should be implemented in torrent tracker
        handler class and must return .torrent filepath
        on success or None on failure."""
        return None

    def debug(self, text):
        """A shortcut to store debug info."""
        self._log.debug(text)


class GenericTrackerHandler(BaseTrackerHandler):
    """Generic torrent tracker handler class implementing
    most common tracker handling methods."""

    def get_id_from_link(self):
        """Returns forum thread identifier from full thread URL."""
        return self.resource_url.split('=')[1]

    def get_torrent_file(self):
        """This is the main method which returns
        a filepath to the downloaded file."""
        torrent_file = None
        download_link = self.get_download_link()
        if download_link is None:
            self.dump_error('Cannot find torrent file download link at %s' % self.resource_url)
        else:
            self.debug('Torrent download link found: %s' % download_link)
            torrent_file = self.download_torrent(download_link)
        return torrent_file

    def get_download_link(self):
        """Tries to find .torrent file download link at forum thread page
        and return that one."""
        raise NotImplementedError()

    def download_torrent(self, url):
        """Gets .torrent file contents from given URL and
        stores that in a temporary file within a filesystem.
        Returns a path to that file.

        """
        raise NotImplementedError()


class GenericPublicTrackerHandler(GenericTrackerHandler):
    """Generic torrent tracker handler class implementing
    most common handling methods for public trackers."""

    login_required = False

    def get_id_from_link(self):
        """Returns forum thread identifier from full thread URL."""
        return self.resource_url.split('/')[-1]

    def download_torrent(self, url):
        """Gets .torrent file contents from given URL and
        stores that in a temporary file within a filesystem.
        Returns a path to that file.

        """
        self.debug('Downloading torrent file from %s ...' % url)
        # That was a check that user himself visited torrent's page ;)
        response, contents = self.get_resource(url)
        return self.store_tmp_torrent(contents)


class GenericPrivateTrackerHandler(GenericPublicTrackerHandler):
    """Generic torrent tracker handler class implementing
    most common handling methods for private trackers (that require
    registration).

    """

    login_required = True
    login_url = None

    # Cookie to verify that a log in was successful.
    cookie_logged_in = None
    logged_in = False
    # Stores a number of login attempts to prevent recursion.
    login_counter = 0

    def get_login_form_data(self, login, password):
        """Should return a dictionary with data to be pushed
        to authorization form.

        """
        return {'username': login, 'password': password}

    def login(self, login, password):
        """Implements tracker login procedure."""
        self.logged_in = False

        if login is None or password is None:
            return False

        self.login_counter += 1

        # No recursion wanted.
        if self.login_counter > 1:
            return False

        self.debug('Trying to login at %s ...' % self.login_url)
        self.get_resource(self.login_url, self.get_login_form_data(login, password))
        cookies = self.get_cookies()

        # Login success check.
        if cookies.get(self.cookie_logged_in) is not None:
            self.logged_in = True
        return self.logged_in

    def before_download(self):
        """Used to perform some required actions right before .torrent download.
        E.g.: to set a sentinel cookie that allows the download."""
        return True

    def download_torrent(self, url):
        """Gets .torrent file contents from given URL and
        stores that in a temporary file within a filesystem.
        Returns a path to that file.

        """
        self.debug('Downloading torrent file from %s ...' % url)
        self.get_cookies()
        self.before_download()
        contents = self.get_resource(url, {})[1]
        return self.store_tmp_torrent(contents)
