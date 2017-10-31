"""
main.py Main file for running Aggregator"
"""
from AggregatorPlugin import AggregatorPlugin

__author__ = "Ofir Yefet"

if __name__ == '__main__':
    # Initialize
    AGGREGATOR = AggregatorPlugin()
    # Run (Blocking)
    AGGREGATOR.start_serve()
