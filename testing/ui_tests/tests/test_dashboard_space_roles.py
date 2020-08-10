from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase
from ui_tests.tests.ui_consts import DEVICES_MODULE, ASSET_NAME_FIELD_NAME


class TestDashboardSpaceRoles(PermissionsTestBase):
    TEST_CHART_TITLE = 'testing drag and drop'
    TEST_CHART_TITLE_MY_DASHBOARD = 'testing drag and drop in my dashboard'

    def _assert_space_for_user(self, user_name, user_password, missing_space_name, exist_space_name):
        self.login_page.switch_user(user_name, user_password)
        # wait for the first spaces fetch to complete
        self.dashboard_page.wait_for_spinner_to_end()
        assert self.dashboard_page.is_missing_space(missing_space_name)
        assert not self.dashboard_page.is_missing_space(exist_space_name)

    def test_dashboard_space_roles(self):
        self.base_page.run_discovery()
        users = []
        user_roles = []
        for i in range(2):
            index_string = str(i)
            users.append(ui_consts.VIEWER_USERNAME + index_string)
            user_roles.append(self.settings_page.add_user_with_duplicated_role(users[i],
                                                                               ui_consts.NEW_PASSWORD,
                                                                               ui_consts.FIRST_NAME,
                                                                               ui_consts.LAST_NAME,
                                                                               self.settings_page.VIEWER_ROLE))
            self.dashboard_page.switch_to_page()
            self.dashboard_page.add_new_space(self.TEST_SPACE_NAME + index_string,
                                              [self.settings_page.VIEWER_ROLE, user_roles[i]])

        for i in range(2):
            missing_space_name = self.TEST_SPACE_NAME + str(abs(i - 1))
            exist_space_name = self.TEST_SPACE_NAME + str(i)
            self._assert_space_for_user(users[i],
                                        ui_consts.NEW_PASSWORD,
                                        missing_space_name,
                                        exist_space_name)

        self.login_page.logout_and_login_with_admin()
        # wait for the first spaces fetch to complete
        self.dashboard_page.wait_for_spinner_to_end()
        for i in range(2):
            assert not self.dashboard_page.is_missing_space(self.TEST_SPACE_NAME + str(i))

    def test_space_drag_and_drop_permission(self):
        self.base_page.run_discovery()
        self.dashboard_page.add_new_space(self.TEST_SPACE_NAME, [self.settings_page.VIEWER_ROLE])
        self.dashboard_page.select_space_by_name(self.TEST_SPACE_NAME)
        self.dashboard_page.add_segmentation_card(module=DEVICES_MODULE,
                                                  field=ASSET_NAME_FIELD_NAME,
                                                  title=self.TEST_CHART_TITLE)
        assert self.dashboard_page.is_drag_and_drop_button_present(self.TEST_CHART_TITLE)
        self.settings_page.add_user(ui_consts.VIEWER_USERNAME,
                                    ui_consts.NEW_PASSWORD,
                                    ui_consts.FIRST_NAME,
                                    ui_consts.LAST_NAME,
                                    self.settings_page.VIEWER_ROLE)
        self.login_page.switch_user(ui_consts.VIEWER_USERNAME, ui_consts.NEW_PASSWORD)
        self.dashboard_page.wait_for_card_spinner_to_end()
        self.dashboard_page.select_space_by_name(self.TEST_SPACE_NAME)
        assert not self.dashboard_page.is_drag_and_drop_button_present(self.TEST_CHART_TITLE)
        self.dashboard_page.select_space_by_name(self.MY_DASHBOARD_TITLE)
        self.dashboard_page.add_segmentation_card(module=DEVICES_MODULE,
                                                  field=ASSET_NAME_FIELD_NAME,
                                                  title=self.TEST_CHART_TITLE_MY_DASHBOARD)
        assert self.dashboard_page.is_drag_and_drop_button_present(self.TEST_CHART_TITLE_MY_DASHBOARD)
        # cleanup
        self.dashboard_page.remove_card(self.TEST_CHART_TITLE_MY_DASHBOARD)
        self.login_page.switch_user(DEFAULT_USER['user_name'], DEFAULT_USER['password'])
        self.dashboard_page.wait_for_card_spinner_to_end()
        self.dashboard_page.select_space_by_name(self.TEST_SPACE_NAME)
        self.dashboard_page.remove_card(self.TEST_CHART_TITLE)
        self.dashboard_page.remove_space()
