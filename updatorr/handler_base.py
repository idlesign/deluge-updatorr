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
