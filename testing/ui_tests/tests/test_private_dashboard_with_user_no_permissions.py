from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase
from ui_tests.tests.ui_consts import (OS_SERVICE_PACK_OPTION_NAME,
                                      OS_TYPE_OPTION_NAME)


class TestPrivateDashboardWithUserNoPermissions(PermissionsTestBase):
    def test_private_dashboard_with_user_no_permissions(self):
        self.base_page.run_discovery()
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.settings_page.wait_for_table_to_load()
        settings_permissions = {
            'dashboard': [
                'View dashboard'
            ],
            'devices_assets': 'all'
        }
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.move_to_space_and_assert_title(2, self.MY_DASHBOARD_TITLE)
        self.dashboard_page.add_segmentation_card(
            'Devices', OS_TYPE_OPTION_NAME, self.TEST_REPORT_NAME)
        card = self.dashboard_page.find_dashboard_card(self.TEST_REPORT_NAME)
        self.dashboard_page.open_edit_card(card)
        self.dashboard_page.select_chart_wizard_field(OS_SERVICE_PACK_OPTION_NAME)
        self.dashboard_page.click_card_save()
        self.dashboard_page.remove_card(self.TEST_REPORT_NAME)
