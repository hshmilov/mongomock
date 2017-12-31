"""
main.py Main file for running Aggregator"
"""
# from watch_service import WatchPlugin

from watch_service import WatchService
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    watch_plugin = WatchService()
    # Run (Blocking)
    watch_plugin.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(WatchService)
