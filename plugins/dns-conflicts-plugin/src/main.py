"""
main.py Main file for running Correlator
"""
from dns_conflicts_plugin import DnsConflictsPlugin
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    plugin = DnsConflictsPlugin()
    # Run (Blocking)
    plugin.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(DnsConflictsPlugin)
