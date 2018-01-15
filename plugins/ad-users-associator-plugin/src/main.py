"""
main.py
"""
from ad_users_associator_plugin import AdUsersAssociatorPlugin
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    plugin = AdUsersAssociatorPlugin()
    # Run (Blocking)
    plugin.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(AdUsersAssociatorPlugin)
