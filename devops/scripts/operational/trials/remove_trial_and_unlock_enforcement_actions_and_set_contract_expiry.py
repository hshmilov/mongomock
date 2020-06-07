import sys

from datetime import datetime

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, FeatureFlagsNames
from testing.services.plugins.core_service import CoreService


def main():
    CoreService().db.gui_config_collection().update_one({
        'config_name': FEATURE_FLAGS_CONFIG
    }, {
        '$set': {
            f'config.{FeatureFlagsNames.TrialEnd}': '',
            f'config.{FeatureFlagsNames.LockedActions}': [],
            f'config.{FeatureFlagsNames.LockOnExpiry}': True,
            f'config.{FeatureFlagsNames.ExpiryDate}':
                (datetime(year=2021, month=5, day=26)).isoformat()[:10].replace('-', '/')
        }
    })
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
