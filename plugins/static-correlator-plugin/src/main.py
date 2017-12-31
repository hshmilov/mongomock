"""
main.py Main file for running Correlator
"""
from static_correlator_plugin import StaticCorrelatorPlugin
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    CORRELATOR = StaticCorrelatorPlugin()

    # Run (Blocking)
    CORRELATOR.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(StaticCorrelatorPlugin)
