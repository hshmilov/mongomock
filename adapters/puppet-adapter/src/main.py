"""main.py: Main file for running puppet plugin"""
# TODO ofri: Change the return values protocol

__author__ = "Ofri Shur"

from puppetadapter import PuppetAdapter
from axonius.ServerUtils import init_wsgi

if __name__ == '__main__':
    # Initialize
    puppet_adapter = PuppetAdapter()

    # Run (Blocking)
    puppet_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(PuppetAdapter)
