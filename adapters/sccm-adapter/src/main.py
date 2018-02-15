"""
main.py Main file for running sccm plugin"
"""


from sccm_adapter import SccmAdapter
from axonius.server_utils import init_wsgi

if __name__ == '__main__':
    # Initialize
    sccm_adapter = SccmAdapter()

    # Run (Blocking)
    sccm_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(SccmAdapter)
