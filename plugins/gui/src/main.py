"""
main.py Main file for running active directory plugin"
"""
from axonius.server_utils import init_wsgi
from backend_plugin import BackendPlugin

__author__ = "Mark Segal"


if __name__ == '__main__':
    # Initialize
    gui = BackendPlugin()
    # Run (Blocking)
    gui.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(BackendPlugin)
