"""
main.py Main file for running splunk plugin"
"""

__author__ = "Tal & Asaf"


from splunk_symantec_adapter import SplunkSymantecAdapter
from axonius.ServerUtils import init_wsgi

if __name__ == '__main__':
    # Initialize
    splunk_symantec_adapter = SplunkSymantecAdapter()

    # Run (Blocking)
    splunk_symantec_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(SplunkSymantecAdapter)
