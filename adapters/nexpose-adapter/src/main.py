from nexposeplugin import NexposePlugin
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    nexpose_adapter = NexposePlugin()

    # Run (Blocking)
    nexpose_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(NexposePlugin)
