from fortigate_adapter import FortigateAdapter
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    fortigate_adapter = FortigateAdapter()

    # Run (Blocking)
    fortigate_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(FortigateAdapter)
