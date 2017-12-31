"""
main.py Main file for running symantec plugin"
"""

__author__ = "Tal & Asaf"


from symantec_adapter import SymantecAdapter
from axonius.server_utils import init_wsgi

if __name__ == '__main__':
    # Initialize
    symantec_adapter = SymantecAdapter()

    # Run (Blocking)
    symantec_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(SymantecAdapter)
