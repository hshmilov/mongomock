#!/home/ubuntu/cortex/pyrun.sh
import sys

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, FeatureFlagsNames
from testing.services.plugins.core_service import CoreService


def main():
    CoreService().db.plugins.gui.configurable_configs.update_config(
        FEATURE_FLAGS_CONFIG,
        {
            FeatureFlagsNames.TrialEnd: ''
        }
    )
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
