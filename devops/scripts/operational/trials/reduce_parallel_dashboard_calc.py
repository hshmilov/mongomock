import sys

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, DashboardControlNames
from testing.services.plugins.core_service import CoreService


def main():
    CoreService().db.plugins.gui.configurable_configs.update_config(
        FEATURE_FLAGS_CONFIG,
        {
            f'{DashboardControlNames.root_key}.{DashboardControlNames.present_call_limit}': 1,
            f'{DashboardControlNames.root_key}.{DashboardControlNames.historical_call_limit}': 1,
        }
    )
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
