from qcore_adapter import QcoreAdapter
from axonius.server_utils import init_wsgi

if __name__ == '__main__':
    # Initialize
    adapter = QcoreAdapter()

    # Run (Blocking)
    adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(QcoreAdapter)
