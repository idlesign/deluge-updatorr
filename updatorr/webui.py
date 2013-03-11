import os
import logging
import pkg_resources
from deluge.common import fspeed
from deluge.ui.client import client
from deluge.plugins.pluginbase import WebPluginBase
from deluge import component

log = logging.getLogger(__name__)

def get_resource(filename):
    return pkg_resources.resource_filename("updatorr",
                                           os.path.join("data", filename))

class WebUI(WebPluginBase):

    scripts = [get_resource("updatorr.js")]
    debug_scripts = scripts
