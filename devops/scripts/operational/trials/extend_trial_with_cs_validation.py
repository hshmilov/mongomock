#!/home/ubuntu/cortex/venv/bin/python
import sys

from datetime import datetime

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, FeatureFlagsNames
from testing.services.plugins.core_service import CoreService

CUSTOMER_ID = ''
TRIAL_EXPIRY_DT = datetime(year=2020, month=10, day=1)


def main():

    # assert current client
    cs = CoreService()

    print(f'Current client {cs.node_id}')
    if CUSTOMER_ID and (cs.node_id != CUSTOMER_ID):
        print(f'Invalid customer')
        return

    CoreService().db.plugins.gui.configurable_configs.update_config(
        FEATURE_FLAGS_CONFIG,
        {
            FeatureFlagsNames.TrialEnd: TRIAL_EXPIRY_DT.isoformat()[:10].replace('-', '/')
        }
    )
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
