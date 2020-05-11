from ui_tests.tests.ui_test_base import TestBase


class PermissionsTestBase(TestBase):

    def _add_action_to_role_and_login_with_user(self, permissions, category, add_action, role, user_name, password):
        self.login_page.logout_and_login_with_admin()
        if not permissions.get(category):
            permissions[category] = []
        permissions[category].append(add_action)
        self.settings_page.update_role(role, permissions, True)
        self.login_page.logout_and_login_with_user(user_name, password=password)
