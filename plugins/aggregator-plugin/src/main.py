"""
main.py Main file for running Aggregator"
"""
from AggregatorPlugin import AggregatorPlugin
from axonius.ServerUtils import init_wsgi

__author__ = "Ofir Yefet"


if __name__ == '__main__':
    # Initialize
    aggregator = AggregatorPlugin()
    # Run (Blocking)
    aggregator.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(AggregatorPlugin)
