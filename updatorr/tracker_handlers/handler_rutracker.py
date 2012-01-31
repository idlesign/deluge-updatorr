from updatorr.handler_base import BaseTrackerHandler
from updatorr.utils import register_tracker_handler


class RutrackerHandler(BaseTrackerHandler):
    """This class implements .torrent files downloads
    for http://rutracker.org tracker."""

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

        login_url = 'http://login.rutracker.org/forum/login.php'
        self.debug('Trying to login at %s ...' % login_url)
        form_data = {
            'login_username': login,
            'login_password': password,
            'login': 'pushed',
            }
        response, page_html = self.get_resource(login_url, form_data)
        if 'set-cookie' not in response:
            self.dump_error('Unable to login.')
        else:
            self.set_cookie(response['set-cookie'].split(';')[0])
            self.logged_in = True

        return self.logged_in

    def get_download_link(self):
        """Tries to find .torrent file download link at forum thread page
        and return that one."""
        response, page_html = self.get_resource(self.resource_url)
        page_links = self.find_links(page_html)
        download_link = None
        for page_link in page_links:
            if 'dl.rutracker.org' in page_link:
                download_link = page_link
                if 'guest' in download_link:
                    download_link = None
                    self.debug('Login is required to download torrent file.')
                    if self.login(self.get_settings('login'), self.get_settings('password')):
                        download_link = self.get_download_link()
                break
        return download_link

    def download_torrent(self, url):
        """Gets .torrent file contents from given URL and
        stores that in a temporary file within a filesystem.
        Returns a path to that file.

        """
        self.debug('Downloading torrent file from %s ...' % url)
        # That was a check that user himself visited torrent's page ;)
        self.set_cookie({'bb_dl': self.get_id_from_link()})
        contents = self.get_resource(url, {})[1]
        return self.store_tmp_torrent(contents)


# With that one we tell updatetorr to handle links to `rutracker.org` domain with RutrackerHandler class.
register_tracker_handler('rutracker.org', RutrackerHandler)
