"""
main.py Main file for running Correlator
"""
from careful_execution_correlator_plugin import CarefulExecutionCorrelatorPlugin
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    CORRELATOR = CarefulExecutionCorrelatorPlugin()
    # Run (Blocking)
    CORRELATOR.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(CarefulExecutionCorrelatorPlugin)
