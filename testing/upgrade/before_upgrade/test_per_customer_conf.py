from exclude_helper import EXCLUDE_LIST_KEY, ADD_TO_EXCLUDE_KEY, REMOVE_FROM_EXCLUDE_KEY
from ui_tests.tests.ui_test_base import TestBase
from upgrade.upgrade_test_utils.customer_conf import write_upgrade_test_customer_conf, read_upgrade_test_customer_data


class TestPerCustomerSettings(TestBase):
    # pylint: disable=no-self-use
    def test_add_nimbul(self):
        conf = read_upgrade_test_customer_data()
        conf[EXCLUDE_LIST_KEY] = {
            ADD_TO_EXCLUDE_KEY: [],
            REMOVE_FROM_EXCLUDE_KEY: ['nimbul']
        }
        write_upgrade_test_customer_conf(conf)
