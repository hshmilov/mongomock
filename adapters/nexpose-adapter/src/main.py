from nexpose_adapter import NexposeAdapter
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    nexpose_adapter = NexposeAdapter()

    # Run (Blocking)
    nexpose_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(NexposeAdapter)
