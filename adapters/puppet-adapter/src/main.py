"""main.py: Main file for running puppet plugin"""
# TODO ofri: Change the return values protocol

__author__ = "Ofri Shur"

from puppetadapter import PuppetAdapter

if __name__ == '__main__':
    # Initialize
    PUPPET_WRAPPER = PuppetAdapter()
    
    # Run (Blocking)
    PUPPET_WRAPPER.start_serve()
