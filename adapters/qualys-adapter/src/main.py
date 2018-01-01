"""
main.py Main file for running qualys plugin"
"""

__author__ = "Tal & Asaf"


from qualys_adapter import QualysAdapter
from axonius.server_utils import init_wsgi

if __name__ == '__main__':
    # Initialize
    qualys_adapter = QualysAdapter()

    # Run (Blocking)
    qualys_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(QualysAdapter)
