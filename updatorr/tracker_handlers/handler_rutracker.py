from updatorr.handler_base import GenericPrivateTrackerHandler
from updatorr.utils import register_tracker_handler


class RutrackerHandler(GenericPrivateTrackerHandler):
    """This class implements .torrent files downloads
    for http://rutracker.org tracker."""

    login_url = 'http://login.rutracker.org/forum/login.php'
    cookie_logged_in = 'bb_data'

    def get_login_form_data(self, login, password):
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'login_username': login, 'login_password': password, 'login': 'pushed'}

    def before_download(self):
        """Used to perform some required actions right before .torrent download."""
        self.set_cookie('bb_dl', self.get_id_from_link())  # A check that user himself have visited torrent's page ;)

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

# With that one we tell updatetorr to handle links to `rutracker.org` domain with RutrackerHandler class.
register_tracker_handler('rutracker.org', RutrackerHandler)
