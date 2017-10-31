"""
main.py Main file for running active directory plugin"
"""
from AWSAdapter import AWSAdapter

__author__ = "Mark Segal"

if __name__ == '__main__':
    # Initialize
    AWS_WRAPPER = AWSAdapter()
    # Run (Blocking)
    AWS_WRAPPER.start_serve()
