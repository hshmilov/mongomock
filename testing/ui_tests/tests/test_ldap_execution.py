# pylint: disable=too-many-statements
import time

from axonius.utils.wait import wait_until
from test_credentials.test_ad_credentials import WMI_QUERIES_DEVICE
from ui_tests.tests.ui_test_base import TestBase

CHANGE_LDAP_ATTRIBUTE_NAME = 'Change LDAP Attribute'
CHANGE_LDAP_ACTION_NAME = 'Change LDAP Enforcement'


class TestLDAPEnforcement(TestBase):
    def test_change_ldap_attribute(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.enforcements_page.create_basic_empty_enforcement(CHANGE_LDAP_ATTRIBUTE_NAME)
        self.enforcements_page.add_ldap_attribute()
        self.enforcements_page.click_save_button()
        self.enforcements_page.wait_for_table_to_load()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.enforce_action_on_query(
            self.devices_page.FILTER_HOSTNAME.format(filter_value=WMI_QUERIES_DEVICE),
            CHANGE_LDAP_ATTRIBUTE_NAME
        )
        self.enforcements_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.enforcements_page.click_tasks_button()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_row()

        def _check_task_finished():
            self.driver.refresh()
            time.sleep(3)
            try:
                assert self.enforcements_page.find_task_action_success(CHANGE_LDAP_ATTRIBUTE_NAME).text == str(1)
                return True
            except Exception:
                return False

        assert wait_until(_check_task_finished, check_return_value=True, total_timeout=60 * 3, interval=5)
