"""
main.py Main file for running Aggregator"
"""
from ExecutionPlugin import ExecutionPlugin
from axonius.ServerUtils import init_wsgi

__author__ = "Ofir Yefet"


if __name__ == '__main__':
    # Initialize
    execution_plugin = ExecutionPlugin()
    # Run (Blocking)
    execution_plugin.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(ExecutionPlugin)
