"""
main.py Main file for running sentinel one plugin"
"""

__author__ = "Tal & Asaf"


from sentinelone_adapter import SentinelOneAdapter
from axonius.server_utils import init_wsgi

if __name__ == '__main__':
    # Initialize
    sentinelone_adapter = SentinelOneAdapter()

    # Run (Blocking)
    sentinelone_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(SentinelOneAdapter)
