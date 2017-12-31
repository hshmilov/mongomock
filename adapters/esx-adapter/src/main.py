"""
main.py Main file for running active directory plugin"
"""
from esx_adapter import ESXAdapter
from axonius.server_utils import init_wsgi

__author__ = "Mark Segal"


def initialize():
    return ESXAdapter()


def wsgi_main(*args, **kwargs):
    """The main method for wsgi apps.

    When in production mode, we use a production server with wsgi support to load our modules.
    so we use this function as a proxy to the real wsgi function flask provides.
    """

    if not hasattr(wsgi_main, "plugin"):
        wsgi_main.plugin = initialize()

    return wsgi_main.plugin.wsgi_app(*args, **kwargs)


if __name__ == '__main__':
    # Initialize
    esx_adapter = ESXAdapter()
    # Run (Blocking)
    esx_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(ESXAdapter)
