"""
main.py Main file for running qualys plugin"
"""

__author__ = "Tal & Asaf"


from qualys_scans_adapter import QualysScansAdapter
from axonius.server_utils import init_wsgi

if __name__ == '__main__':
    # Initialize
    qualys_scans_adapter = QualysScansAdapter()

    # Run (Blocking)
    qualys_scans_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(QualysScansAdapter)
