import os
import re
import tempfile
from urllib import urlencode
from httplib2 import Http


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
        if 'cookies' in setting and setting['cookies'] is not None:
            for param, value in setting['cookies'].items():
                self.set_cookie({param: value})

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

    def get_basic_headers(self):
        """Returns a dictionary with basic HTTP headers
        that can be used in HTTP requests.

        Note that this headers also include cookies information
        is such is available.

        """
        headers = {'User-agent': 'Mozilla/5.0 (Ubuntu; X11; Linux i686; rv:8.0) Gecko/20100'}
        cookie_str = self.get_cookies()
        if cookie_str is not None:
            headers['Cookie'] = cookie_str
        self.debug('Request headers: %s' % headers)
        return headers

    def get_resource(self, url, form_data=None):
        """Returns an HTTP resource data from given URL.
        If a dictionary is passed in `form_data` POST HTTP method
        would be used to pass data to resource (even if that dictionary is empty).

        """
        self.debug('Getting page at %s ...' % url)
        http = Http()
        headers = self.get_basic_headers()
        method = 'GET'
        body = None
        if form_data is not None:
            method = 'POST'
            body = urlencode(form_data)
            headers['Content-type'] = 'application/x-www-form-urlencoded'
        return http.request(url, method=method, body=body, headers=headers)

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

    def set_cookie(self, data):
        """Stores cookie data into the registry for further usage.
        Data could be a dictionary like {param: value},
        or a string, e.g. `param=value`.

        Note that cookie registry data is updated with new values,
        but not replaced.

        """
        global COOKIES_REGISTRY
        if isinstance(data, str):
            data = dict([data.split('=')])
        if self.tracker_host in COOKIES_REGISTRY:
            COOKIES_REGISTRY[self.tracker_host].update(data)
        else:
            COOKIES_REGISTRY[self.tracker_host] = data

    def get_cookies(self, as_dict=False):
        """Returns a string with cookies for this tracker."""
        if self.tracker_host in COOKIES_REGISTRY:
            if as_dict:
                return COOKIES_REGISTRY[self.tracker_host]
            cookie_str = ';'.join(['%s=%s' % (k, v) for k, v in COOKIES_REGISTRY[self.tracker_host].items()])
            return cookie_str
        return None

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
