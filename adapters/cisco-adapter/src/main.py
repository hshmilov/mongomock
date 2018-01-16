"""
main.py Main file for running active directory plugin"
"""
from cisco_adapter import CiscoAdapter
from axonius.server_utils import init_wsgi

if __name__ == '__main__':
    # Initialize
    adapter = CiscoAdapter()

    # Run (Blocking)
    adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(CiscoAdapter)
