import pytest
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.gui_consts import DASHBOARD_SPACE_PERSONAL
from axonius.utils.wait import wait_until
from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase


# pylint: disable=no-member


class TestDashboardPermissions(PermissionsTestBase):

    TEST_EMPTY_TITLE = 'test empty'
    OSX_OPERATING_SYSTEM_NAME = 'OS X Operating System'
    OSX_OPERATING_SYSTEM_FILTER = 'specific_data.data.os.type == "OS X"'

    TEST_SPACE_NAME = 'test space'
    TEST_SPACE_NAME_RENAME = 'test rename'
    TEST_RENAME_SPACE_NAME = 'rename space'
    NOTE_TEXT = 'note text'

    def test_dashboard_permissions(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_new_space(self.TEST_RENAME_SPACE_NAME)

        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)

        settings_permissions = {
            'dashboard': [],
            'devices_assets': [
                'Run saved queries',
                'Create saved query',
            ]
        }

        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.is_missing_space(DASHBOARD_SPACE_PERSONAL)
        assert self.dashboard_page.is_new_chart_card_missing()
        with pytest.raises(NoSuchElementException):
            self.dashboard_page.find_search_insights()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'View devices',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_search_insights()
        self.dashboard_page.fill_query_value('cb')
        self.dashboard_page.enter_search()
        self.dashboard_page.wait_for_table_to_load()
        assert len(self.dashboard_page.get_search_insights_tables()) == 1
        self.dashboard_page.assert_device_explorer_results_exists()

        self._test_chart_permissions(settings_permissions, user_role)
        self._test_spaces_permissions(settings_permissions, user_role)
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'View users',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_search_insights()
        self.dashboard_page.fill_query_value('cb')
        self.dashboard_page.enter_search()
        self.dashboard_page.wait_for_table_to_load()
        assert len(self.dashboard_page.get_search_insights_tables()) == 2
        self.dashboard_page.assert_device_explorer_results_exists()
        self.dashboard_page.assert_users_explorer_results_exists()

    def _test_chart_permissions(self, settings_permissions, user_role):
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'dashboard',
                                                     'Add chart',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        assert not self.dashboard_page.is_missing_space(DASHBOARD_SPACE_PERSONAL)
        self.dashboard_page.click_tab(DASHBOARD_SPACE_PERSONAL)
        assert not self.dashboard_page.is_new_chart_card_missing()
        self.devices_page.create_saved_query(self.OSX_OPERATING_SYSTEM_FILTER, self.OSX_OPERATING_SYSTEM_NAME)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card(module='Devices',
                                                  field=ui_consts.OS_TYPE_OPTION_NAME,
                                                  title=self.TEST_EMPTY_TITLE,
                                                  view_name=self.OSX_OPERATING_SYSTEM_NAME)
        assert not self.dashboard_page.is_remove_card_button_present(self.TEST_EMPTY_TITLE)
        assert not self.dashboard_page.is_edit_card_button_present(self.TEST_EMPTY_TITLE)
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'dashboard',
                                                     'Edit charts',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.click_tab(DASHBOARD_SPACE_PERSONAL)
        assert not self.dashboard_page.is_remove_card_button_present(self.TEST_EMPTY_TITLE)
        assert self.dashboard_page.is_edit_card_button_present(self.TEST_EMPTY_TITLE)
        self.dashboard_page.edit_card(self.TEST_EMPTY_TITLE)
        self.dashboard_page.click_card_save()
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'dashboard',
                                                     'Delete chart',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.click_tab(DASHBOARD_SPACE_PERSONAL)
        assert self.dashboard_page.is_remove_card_button_present(self.TEST_EMPTY_TITLE)
        assert self.dashboard_page.is_edit_card_button_present(self.TEST_EMPTY_TITLE)
        self.dashboard_page.remove_card(self.TEST_EMPTY_TITLE)

    def _test_spaces_permissions(self, settings_permissions, user_role):
        assert self.dashboard_page.is_missing_add_space()
        self.dashboard_page.assert_disabled_rename_space(3)
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'dashboard',
                                                     'Add space',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        assert not self.dashboard_page.is_missing_add_space()
        self.dashboard_page.add_new_space(self.TEST_SPACE_NAME)
        wait_until(lambda: self.dashboard_page.find_space_header_title(4) == self.TEST_SPACE_NAME)
        assert self.dashboard_page.is_missing_remove_space(4)
        self.dashboard_page.rename_space(self.TEST_SPACE_NAME_RENAME, 4)
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'dashboard',
                                                     'Delete space',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        assert not self.dashboard_page.is_missing_add_space()
        assert not self.dashboard_page.is_missing_remove_space()
        self.dashboard_page.remove_space()
        self.dashboard_page.remove_space()
