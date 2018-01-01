"""
main.py Main file for running active directory plugin"
"""
from aws_adapter import AWSAdapter
from axonius.server_utils import init_wsgi

__author__ = "Mark Segal"


if __name__ == '__main__':
    # Initialize
    adapter = AWSAdapter()

    # Run (Blocking)
    adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(AWSAdapter)
