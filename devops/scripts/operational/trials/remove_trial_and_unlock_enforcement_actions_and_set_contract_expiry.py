import sys

from datetime import datetime

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, FeatureFlagsNames
from testing.services.plugins.core_service import CoreService


def main():
    CoreService().db.plugins.gui.configurable_configs.update_config(
        FEATURE_FLAGS_CONFIG,
        {
            FeatureFlagsNames.TrialEnd: '',
            FeatureFlagsNames.LockedActions: [],
            FeatureFlagsNames.LockOnExpiry: True,
            FeatureFlagsNames.ExpiryDate: (datetime(year=2021, month=5, day=26)).isoformat()[:10].replace('-', '/')
        }
    )
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
