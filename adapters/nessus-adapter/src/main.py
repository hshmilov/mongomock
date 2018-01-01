"""
main.py Main file for running Nessus adapter"
"""
__author__ = "Shira Gold"

from nessus_adapter import NessusAdapter
from axonius.server_utils import init_wsgi

if __name__ == '__main__':
    # Initialize
    symantec_adapter = NessusAdapter()

    # Run (Blocking)
    symantec_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(NessusAdapter)
