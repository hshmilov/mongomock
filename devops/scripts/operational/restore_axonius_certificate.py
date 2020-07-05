"""
Restores the gui ssl settings to False and set the axonius default self sign certificate
"""
import sys

from axonius.consts.core_consts import CORE_CONFIG_NAME
from testing.services.plugins.gui_service import GuiService
from testing.services.plugins.core_service import CoreService


def main():
    CoreService().db.plugins.core.configurable_configs.update_config(
        CORE_CONFIG_NAME,
        {
            f'global_ssl.enabled': False,
            f'global_ssl.cert_file': '',
            f'global_ssl.private_key': '',
            f'global_ssl.passphrase': '',
            f'global_ssl.hostname': ''
        }
    )
    GuiService().restart()
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
