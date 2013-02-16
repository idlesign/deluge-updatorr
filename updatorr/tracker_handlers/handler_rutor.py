# -*- coding: utf-8 -*-
"""
Created on Sat Feb 16 14:17:04 2013

@author: lucky
"""

from updatorr.handler_base import BaseTrackerHandler
from updatorr.utils import register_tracker_handler


class RutorHandler(BaseTrackerHandler):
    """This class implements .torrent files downloads
    for http://rutor.org tracker."""
    
    login_required = False

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
        lst = self.resource_url.split('/')
        lst.reverse ()
        return lst[0]

    def get_download_link(self):
        """Tries to find .torrent file download link at forum thread page
        and return that one."""
        linkToFind = "d.rutor.org/download/" + self.get_id_from_link()
        response, page_html = self.get_resource(self.resource_url)
        page_links = self.find_links(page_html)
        download_link = None
        for page_link in page_links:
            if linkToFind in page_link:
                download_link = page_link
                break
        return download_link

    def download_torrent(self, url):
        """Gets .torrent file contents from given URL and
        stores that in a temporary file within a filesystem.
        Returns a path to that file.

        """
        self.debug('Downloading torrent file from %s ...' % url)
        # That was a check that user himself visited torrent's page ;)
        response, contents = self.get_resource(url)
        return self.store_tmp_torrent(contents)


# With that one we tell updatetorr to handle links to `rutracker.org` domain with RutrackerHandler class.
register_tracker_handler('rutor.org', RutorHandler)
