"""main.py: Main file for running active directory plugin"""
# TODO ofir: Change the return values protocol

__author__ = "Ofir Yefet"

from ActiveDirectoryPlugin import ActiveDirectoryPlugin
from axonius.ServerUtils import init_wsgi

if __name__ == '__main__':
    # Initialize
    ad_adapter = ActiveDirectoryPlugin()

    # Run (Blocking)
    ad_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(ActiveDirectoryPlugin)
