"""
main.py Main file for running splunk plugin"
"""

__author__ = "Tal & Asaf"


from splunk_nexpose_adapter import SplunkNexposeAdapter
from axonius.ServerUtils import init_wsgi

if __name__ == '__main__':
    # Initialize
    splunk_nexpose_adapter = SplunkNexposeAdapter()

    # Run (Blocking)
    splunk_nexpose_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(SplunkNexposeAdapter)
