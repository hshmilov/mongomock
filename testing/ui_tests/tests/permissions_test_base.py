import pytest
from selenium.common.exceptions import NoSuchElementException

from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase


class PermissionsTestBase(TestBase):
    TEST_SPACE_NAME = 'test space'
    TEST_REPORT_NAME = 'testonius'
    MY_DASHBOARD_TITLE = 'My Dashboard'

    def _add_action_to_role_and_login_with_user(self,
                                                permissions,
                                                category,
                                                add_action,
                                                role,
                                                user_name,
                                                password,
                                                wait_for_getting_started=True):
        self.login_page.logout_and_login_with_admin(wait_for_getting_started)
        if not permissions.get(category):
            permissions[category] = []
        permissions[category].append(add_action)
        self.settings_page.update_role(role, permissions, True)
        self.login_page.switch_user(user_name,
                                    password,
                                    None,
                                    wait_for_getting_started=wait_for_getting_started)

    def _assert_viewer_role(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(ui_consts.AD_ADAPTER_NAME)
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.assert_new_server_button_is_disabled()
        self.enforcements_page.switch_to_page()
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.find_new_enforcement_button()
        self.reports_page.switch_to_page()
        with pytest.raises(NoSuchElementException):
            self.reports_page.find_new_report_button()
        self.reports_page.is_disabled_new_report_button()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.users_page.click_row()
        with pytest.raises(NoSuchElementException):
            self.devices_page.add_new_tags([ui_consts.TAG_NAME])
        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_load()
        self.users_page.click_row()
        with pytest.raises(NoSuchElementException):
            self.devices_page.add_new_tags([ui_consts.TAG_NAME])
        self.instances_page.switch_to_page()
        self.instances_page.wait_for_table_to_load()
        assert self.instances_page.is_connect_node_disabled()
        self.settings_page.assert_screen_is_restricted()
