"""
main.py Main file for running the adapter.
"""
from traiana_lab_machines_adapter import TraianaLabMachinesAdapter
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    adapter = TraianaLabMachinesAdapter()

    # Run (Blocking)
    adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(TraianaLabMachinesAdapter)
