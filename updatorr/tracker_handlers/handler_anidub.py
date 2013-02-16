from updatorr.handler_base import BaseTrackerHandler
from updatorr.utils import register_tracker_handler
import urllib2


class AnidubHandler(BaseTrackerHandler):
    """This class implements .torrent files downloads
    for http://tr.anidub.com tracker."""

    logged_in = False
    # Stores a number of login attempts to prevent recursion.
    login_counter = 0

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

    def get_id_from_link(self):
        """Returns forum thread identifier from full thread URL."""
        return self.resource_url.split('=')[1]

    def login(self, login, password):
        """Implements tracker login procedure."""
        self.logged_in = False

        if login is None or password is None:
            return False

        self.login_counter += 1

        # No recursion wanted.
        if self.login_counter > 1:
            return False

        login_url = 'http://tr.anidub.com/takelogin.php'
        self.debug('Trying to login at %s ...' % login_url)
        form_data = {
            'username': login,
            'password': password,
            }
        self.get_resource(login_url, form_data)
        cookies = self.get_cookies()

        # Login success check.
        if cookies.get('uid') is not None:
            self.logged_in = True
        return self.logged_in

    def get_download_link(self):
        """Tries to find .torrent file download link at forum thread page
        and return that one."""
        response, page_html = self.get_resource(self.resource_url)
        page_links = self.find_links(page_html)
        download_link = None
        for page_link in page_links:
            if 'login.php?returnto=' in page_link:
                download_link = None
                self.debug('Login is required to download torrent file.')
                if self.login(self.get_settings('login'), self.get_settings('password')):
                    download_link = self.get_download_link()
            if 'download.php?id=' in page_link:
                download_link = 'http://tr.anidub.com/'+urllib2.unquote(page_link).replace("&amp;", "&")
        return download_link

    def download_torrent(self, url):
        """Gets .torrent file contents from given URL and
        stores that in a temporary file within a filesystem.
        Returns a path to that file.

        """
        self.debug('Downloading torrent file from %s ...' % url)
        # That was a check that user himself visited torrent's page ;)
        cookies = self.get_cookies()
        #self.set_cookie('uid', self.get_id_from_link())
        contents = self.get_resource(url, {})[1]
        return self.store_tmp_torrent(contents)


# With that one we tell updatetorr to handle links to `rutracker.org` domain with RutrackerHandler class.
register_tracker_handler('tr.anidub.com', AnidubHandler)
