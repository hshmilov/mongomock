import sys

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, RootMasterNames
from testing.services.plugins.core_service import CoreService


def main():
    CoreService().db.plugins.gui.configurable_configs.update_config(
        FEATURE_FLAGS_CONFIG,
        {
            f'{RootMasterNames.root_key}.{RootMasterNames.enabled}': True
        }
    )
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
