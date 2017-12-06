"""
main.py Main file for running active directory plugin"
"""
from AWSAdapter import AWSAdapter
from axonius.ServerUtils import init_wsgi

__author__ = "Mark Segal"


def initialize():
    return AWSAdapter()


def wsgi_main(*args, **kwargs):
    """The main method for wsgi apps.

    When in production mode, we use a production server with wsgi support to load our modules.
    so we use this function as a proxy to the real wsgi function flask provides.
    """

    if not hasattr(wsgi_main, "plugin"):
        wsgi_main.plugin = initialize()

    return wsgi_main.plugin.wsgi_app(*args, **kwargs)


if __name__ == '__main__':
    # Initialize
    aws_adapter = AWSAdapter()
    # Run (Blocking)
    aws_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(AWSAdapter)
