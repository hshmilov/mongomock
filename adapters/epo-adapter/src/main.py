from epo_plugin import EpoPlugin
from axonius.server_utils import init_wsgi

import ssl

# our epo server has no cert ...
# TODO: remove that in prod

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context


if __name__ == '__main__':
    # Initialize
    epo_adapter = EpoPlugin()

    # Run (Blocking)
    epo_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(EpoPlugin)
