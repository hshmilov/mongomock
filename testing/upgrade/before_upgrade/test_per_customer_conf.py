import os

from axonius.consts.system_consts import LOGS_PATH_HOST
from exclude_helper import (ADD_TO_EXCLUDE_KEY, EXCLUDE_LIST_KEY,
                            REMOVE_FROM_EXCLUDE_KEY)
from ui_tests.tests.ui_test_base import TestBase
from upgrade.upgrade_test_utils.customer_conf import (read_upgrade_test_customer_data,
                                                      write_upgrade_test_customer_conf)


class TestPerCustomerSettings(TestBase):
    # pylint: disable=no-self-use
    def test_add_nimbul(self):
        conf = read_upgrade_test_customer_data()
        conf[EXCLUDE_LIST_KEY] = {
            ADD_TO_EXCLUDE_KEY: [],
            REMOVE_FROM_EXCLUDE_KEY: ['nimbul']
        }
        write_upgrade_test_customer_conf(conf)
        # Making sure that nimbul was not raised (No logs for nimbul were generated).
        assert not any('nimbul' in current_dir for current_dir in os.listdir(LOGS_PATH_HOST))
