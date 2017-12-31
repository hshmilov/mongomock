"""
main.py Main file for running Correlator
"""
from execution_correlator_plugin import ExecutionCorrelatorPlugin
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    CORRELATOR = ExecutionCorrelatorPlugin()
    # Run (Blocking)
    CORRELATOR.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(ExecutionCorrelatorPlugin)
