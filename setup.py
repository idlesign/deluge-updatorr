import os
from setuptools import setup
from updatorr import VERSION


f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
readme = f.read()
f.close()

__plugin_name__ = 'Updatorr'
__version__ = '.'.join(map(str, VERSION))
__description__ = 'Deluge plugin for automatic torrents updates'
__long_description__ = readme
__author__ = "Igor 'idle sign' Starikov"
__author_email__ = 'idlesign@yandex.ru'
__license__ = 'BSD License'
__url__ = 'http://github.com/idlesign/deluge-updatorr'
__pkg_data__ = {__plugin_name__.lower(): ['tracker_handlers/*', 'data/*']}

setup(
    name=__plugin_name__,
    version=__version__,
    description=__description__,
    long_description=__long_description__,
    author=__author__,
    author_email=__author_email__,
    url=__url__,
    license=__license__,
    install_requires=['setuptools'],
    zip_safe=False,

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python'
    ],

    packages=[__plugin_name__.lower()],
    package_data=__pkg_data__,

    entry_points='''
    [deluge.plugin.core]
    %s = %s:CorePlugin
    [deluge.plugin.gtkui]
    %s = %s:GtkUIPlugin
    [deluge.plugin.web]
    %s = %s:WebUIPlugin
    ''' % ((__plugin_name__, __plugin_name__.lower()) * 3)
)
