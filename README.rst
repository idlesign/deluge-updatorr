deluge-updatorr
===============
http://github.com/idlesign/deluge-updatorr


What's that
-----------

*deluge-updatorr is a Deluge plugin for automatic torrents updates.*

If you're periodically checking your favourite torrent tracker site,
on which torrents are organized as articles (i.e forum-like tracker),
to verify whether specific torrents have been updated (e.g. torrent
bundling some TV-series is updated with a new episode), then Updatorr
is might be of use.

You activate Updatorr plugin, set autoupdate period and trackers sites
credentials, choose torrents to be updated from Deluge torrents list,
and Updatorr will do checks for you. When torrent update is available,
Updatorr will replace old torrent with an updated one, and download
new files from new torrent.

Automatic updates are available for:

    * RuTracker.org (ex torrents.ru) - http://rutracker.org/
    * RUTOR - http://rutor.org/
    * AniDUB - http://tr.anidub.com/

*Deluge is a lightweight, Free Software, cross-platform BitTorrent client.*
Download it at http://deluge-torrent.org/


Installation
------------

Open Deluge, go to "Preferences -> Plugins -> Install plugin" and choose
Updatorr .egg file.

If you are to build .egg file from source code yourself use
`python setup.py bdist_egg` command in source code root directory.


Troubleshooting
---------------

Q: I installed Updatorr and checked it on plugins page, but Updatorr
page is not shown in preferences dialog.

A: 1. Verify that you downloaded and installed Updatorr for the same Python
      version your Deluge is working on. Updatorr is available from PyPI
      in distribution for Python 2.7.

   2. Verify that `python-setuptools` package is installed.


Q: It seems that Updatorr doesn't work with my OS/Python/Deluge/GTK+ versions.

A: Updatorr is developed and used with Ubuntu, Python 2.7, Deluge 1.3.3, GTK+ 2.24.
It may or may not work with other software. Anyway you're always welcome to improve Updatorr
to support those (see `Get involved` section down below).



Trackers Handlers
-----------------

*The information below is intended for those wishing to
enable Updatorr autoupdates for their favourite tracker site.*

In order to perform automatic updates Updatorr should be instructed
how to perform those, as different torrent tracking sites require
different machinery to get updated torrents.

Tracker handlers are nothing more as relatively simple scripts
in great Python programming language.

To create a tracker handler class one needs to:

    0. Have essential knowledge in Python programming;
    1. Get Updatorr source code from http://github.com/idlesign/deluge-updatorr/;
    2. Create ``hander_{mytracker}.py`` file under `updatorr/tracker_handlers/`;
    3. In that file subclass ``BaseTrackerHandler`` and implement
       its ``get_torrent_file()`` method;
       Note: See base class properties and methods, as they might be of use.
    4. In that file register you class with ``register_tracker_handler()``.

Tracker handler sample `updatorr/tracker_handlers/handler_mytrack.py`::

    from updatorr.handler_base import BaseTrackerHandler
    from updatorr.utils import register_tracker_handler

    class MyTrackHandler(BaseTrackerHandler):

        # Let's suppose that tracker site doesn't require authorization.
        login_required = False

        def get_torrent_file(self):
            # Here one should implement .torrent file download and
            # save into filesystem. See BaseTrackerHandler fo helper methods.
            torrent_filepath = '/somewhere/in/my/filesystem/new.torrent'
            return torrent_filepath

    register_tracker_handler('mytrackaurl.com', MyTrackHandler)
    register_tracker_handler('yotr.su', MyTrackHandler)

It is not that as if only the `BaseTrackerHandler` class is at your service.
You can speed up your development using `GenericTrackerHandler`, `GenericPublicTrackerHandler`
and `GenericPrivateTrackerHandler` classes, each on which introduces different levels of abstraction.

See `updatorr/tracker_handlers/handler_rutracker.py` and `updatorr/handler_base.py` for reference.
Read docstrings of Updatorr.


Get involved into deluge-updatorr
---------------------------------

**Submit issues.** If you spotted something weird in application behavior or want to propose a feature you can do that at https://github.com/idlesign/deluge-updatorr/issues

**Write code.** If you are eager to participate in application development, fork it at https://github.com/idlesign/deluge-updatorr, write your code, whether it should be a bugfix or a feature implementation, and make a pull request right from the forked project page.

**Spread the word.** If you have some tips and tricks or any other words in mind that you think might be of interest for the others — publish it.


The tip
-------

You might be interested in considering other Deluge plugins at http://dev.deluge-torrent.org/wiki/Plugins/