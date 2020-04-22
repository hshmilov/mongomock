import sys

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, FeatureFlagsNames, CloudComplianceNames
from testing.services.plugins.core_service import CoreService


def main():
    CoreService().db.gui_config_collection().update_one({
        'config_name': FEATURE_FLAGS_CONFIG
    }, {
        '$set': {
            f'config.{FeatureFlagsNames.CloudCompliance}.{CloudComplianceNames.Visible}': True,
            f'config.{FeatureFlagsNames.CloudCompliance}.{CloudComplianceNames.Enabled}': True,
        }
    })
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
