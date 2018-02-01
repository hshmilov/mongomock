"""
main.py
"""
from general_info_plugin import GeneralInfoPlugin
from axonius.server_utils import init_wsgi


if __name__ == '__main__':
    # Initialize
    plugin = GeneralinfoPlugin()
    # Run (Blocking)
    plugin.start_serve()

# Init wsgi if in it.
wsgi_app = init_wsgi(GeneralInfoPlugin)
