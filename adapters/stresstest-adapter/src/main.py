"""main.py: Main file for running Stress test plugin"""

from stress_adapter import StressAdapter
from axonius.server_utils import init_wsgi

if __name__ == '__main__':
    # Initialize
    stress_adapter = StressAdapter()

    # Run (Blocking)
    stress_adapter.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(StressAdapter)
