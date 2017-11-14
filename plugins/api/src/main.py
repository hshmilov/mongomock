"""
main.py Main file for running active directory plugin"
"""
from api_plugin import APIPlugin

__author__ = "Mark Segal"


def initialize():
    return APIPlugin()


def wsgi_main(*args, **kwargs):
    """The main method for wsgi apps.

    When in production mode, we use a production server with wsgi support to load our modules.
    so we use this function as a proxy to the real wsgi function flask provides.
    """

    # This has to be static, since wsgi_main is called a lot.
    if not hasattr(wsgi_main, "plugin"):
        wsgi_main.plugin = initialize()

    return wsgi_main.plugin.wsgi_app(*args, **kwargs)


if __name__ == '__main__':
    # Initialize
    GUI = APIPlugin()
    # Run (Blocking)
    GUI.start_serve()
