"""
main.py Main file for running CSV plugin.
"""
from csv_adapter import CSVAdapter
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    adapter = CSVAdapter()

    # Run (Blocking)
    adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(CSVAdapter)
