from ui_tests.tests.ui_test_base import TestBase


class PermissionsTestBase(TestBase):

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
