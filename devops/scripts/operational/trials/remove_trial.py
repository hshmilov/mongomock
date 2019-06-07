"""
Removes the trial. This is done for operational reasons where we have to send this file to an offline customer.
Do not send the py file, instead, send the pyc file in this folder.
To compile it, run in bash `python3 -m compileall .`
"""
import sys

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, FeatureFlagsNames
from testing.services.plugins.core_service import CoreService


def main():
    CoreService().db.gui_config_collection().update_one({
        'config_name': FEATURE_FLAGS_CONFIG
    }, {
        '$set': {
            f'config.{FeatureFlagsNames.TrialEnd}': ''
        }
    })
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
