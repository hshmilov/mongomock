#!/home/ubuntu/cortex/pyrun.sh
import sys

from datetime import datetime

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, FeatureFlagsNames
from testing.services.plugins.core_service import CoreService


def main():
    CoreService().db.plugins.gui.configurable_configs.update_config(
        FEATURE_FLAGS_CONFIG,
        {
            FeatureFlagsNames.TrialEnd: (datetime(year=2020, month=1, day=31)).isoformat()[:10].replace('-', '/')
        }
    )
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
