from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase


class TestDashboardSpaceRoles(PermissionsTestBase):
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
