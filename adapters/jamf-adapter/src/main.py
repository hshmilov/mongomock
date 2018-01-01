"""
main.py Main file for running jamf plugin"
"""

__author__ = "Tal & Asaf"


from jamf_adapter import JamfAdapter
from axonius.server_utils import init_wsgi

if __name__ == '__main__':
    # Initialize
    jamf_adapter = JamfAdapter()

    # Run (Blocking)
    jamf_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(JamfAdapter)
