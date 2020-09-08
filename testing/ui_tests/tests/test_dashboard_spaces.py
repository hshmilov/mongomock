from axonius.consts.gui_consts import (DASHBOARD_SPACE_DEFAULT,
                                       DASHBOARD_SPACE_PERSONAL)
from axonius.utils.wait import wait_until
from test_credentials.test_gui_credentials import AXONIUS_USER
from ui_tests.tests.test_dashboard_chart_base import TestDashboardChartBase
from ui_tests.tests.ui_consts import (FIRST_NAME, LAST_NAME, NEW_PASSWORD,
                                      OS_TYPE_OPTION_NAME, READ_ONLY_USERNAME,
                                      READ_WRITE_USERNAME)

# pylint: disable=no-member


class TestDashboardSpaces(TestDashboardChartBase):
    COVERAGE_SPACE_NAME = 'Coverage Dashboard'
    VULNERABILITY_SPACE_NAME = 'Vulnerability Dashboard'
    PERSONAL_SPACE_PANEL_NAME = 'Private Segment OS'

    def _test_read_only_user_with_dashboard_read_write(self):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        # Login with Admin user and change the read only Dashboard permission
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'],
                              wait_for_getting_started=True)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.wait_for_table_to_load()
        user = self.settings_page.get_user_object_by_user_name(READ_ONLY_USERNAME)
        self.settings_page.click_manage_roles_settings()
        self.settings_page.wait_for_table_to_load()
        self.settings_page.click_role_by_name(user.role)
        self.settings_page.wait_for_side_panel()
        self.settings_page.get_role_edit_panel_action().click()
        self.settings_page.select_permissions({
            'dashboard': 'all'
        })
        self.settings_page.click_save_button()
        self.settings_page.safeguard_click_confirm('Yes')
        self.settings_page.wait_for_role_successfully_saved_toaster()

        self.dashboard_page.switch_to_page()
        # Login with Read Only user and see it can see personal space and add a chart
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_ONLY_USERNAME, password=NEW_PASSWORD,
                              wait_for_getting_started=False)
        self.dashboard_page.switch_to_page()
        assert not self.dashboard_page.is_missing_space(DASHBOARD_SPACE_PERSONAL)
        self.dashboard_page.click_space_by_name(DASHBOARD_SPACE_PERSONAL)
        assert not self.dashboard_page.is_element_disabled(self.dashboard_page.find_new_chart_card())

    def test_dashboard_spaces(self):
        # Default space and Personal space existing
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_active_space_header_title() == DASHBOARD_SPACE_DEFAULT
        assert self.dashboard_page.find_space_header_title(2) == DASHBOARD_SPACE_PERSONAL

        # Add new space and name it
        self.dashboard_page.add_new_space(self.COVERAGE_SPACE_NAME)
        wait_until(lambda: self.dashboard_page.find_space_header_title(3) == self.COVERAGE_SPACE_NAME)

        # Rename an existing space
        self.dashboard_page.edit_space(self.VULNERABILITY_SPACE_NAME, index=3)
        wait_until(lambda: self.dashboard_page.find_space_header_title(3) == self.VULNERABILITY_SPACE_NAME)
        assert self.dashboard_page.is_missing_space(self.COVERAGE_SPACE_NAME)
        self.dashboard_page.add_new_space(self.COVERAGE_SPACE_NAME)

        # Add a panel to a custom space
        self.dashboard_page.find_space_header(3).click()
        self.dashboard_page.add_segmentation_card('Devices', OS_TYPE_OPTION_NAME, self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.wait_for_spinner_to_end()
        segment_card = self.dashboard_page.get_card(self.CUSTOM_SPACE_PANEL_NAME)
        assert segment_card and self.dashboard_page.get_histogram_chart_from_card(segment_card)
        self.dashboard_page.find_space_header(1).click()
        assert self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.find_space_header(2).click()
        assert self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)

        # Add a panel to the Personal space and check hidden from other user
        self.dashboard_page.add_segmentation_card('Devices', OS_TYPE_OPTION_NAME, self.PERSONAL_SPACE_PANEL_NAME)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(READ_WRITE_USERNAME, NEW_PASSWORD,
                                           FIRST_NAME, LAST_NAME,
                                           role_name=self.settings_page.ADMIN_ROLE)
        self.settings_page.add_user_with_duplicated_role(READ_ONLY_USERNAME, NEW_PASSWORD,
                                                         FIRST_NAME, LAST_NAME,
                                                         role_to_duplicate=self.settings_page.VIEWER_ROLE)
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_WRITE_USERNAME, password=NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.find_space_header(2).click()
        assert self.dashboard_page.is_missing_panel(self.PERSONAL_SPACE_PANEL_NAME)
        assert not self.dashboard_page.is_missing_space(self.VULNERABILITY_SPACE_NAME)
        self.dashboard_page.find_space_header(3).click()
        assert not self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.remove_card(self.CUSTOM_SPACE_PANEL_NAME)
        assert not self.dashboard_page.is_missing_space(self.COVERAGE_SPACE_NAME)
        self.dashboard_page.remove_space(3)
        self.dashboard_page.edit_space(self.VULNERABILITY_SPACE_NAME, index=3)

        # Remove a space
        assert self.dashboard_page.is_missing_space(self.COVERAGE_SPACE_NAME)
        self.dashboard_page.remove_space(3)
        assert self.dashboard_page.is_missing_space(self.VULNERABILITY_SPACE_NAME)

        # Login with Read Only user and see it cannot add a space
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_ONLY_USERNAME, password=NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.is_missing_add_space()
        self._test_read_only_user_with_dashboard_read_write()
