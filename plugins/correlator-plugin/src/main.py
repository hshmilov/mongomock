"""
main.py Main file for running Correlator
"""
from CorrelatorPlugin import CorrelatorPlugin
from axonius.ServerUtils import init_wsgi


if __name__ == '__main__':
    # Initialize
    CORRELATOR = CorrelatorPlugin()
    # Run (Blocking)
    CORRELATOR.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(CorrelatorPlugin)
