from eset_adapter import EsetAdapter
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    eset_adapter = EsetAdapter()

    # Run (Blocking)
    eset_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(EsetAdapter)
