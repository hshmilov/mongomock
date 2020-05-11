from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase

# pylint: disable=no-member


class TestInstancesPermissions(PermissionsTestBase):

    def test_instances_permissions(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.settings_page.wait_for_table_to_load()
        settings_permissions = {
            'instances': [
                'View instances'
            ]
        }
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.instances_page.switch_to_page()
        self.instances_page.click_query_row_by_name('Master')
        assert not self.instances_page.find_instance_name_textbox().is_enabled()
        assert not self.instances_page.find_instance_hostname_textbox().is_enabled()
        assert not self.instances_page.get_save_button().is_enabled()
        self.instances_page.get_cancel_button().click()
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'instances',
                                                     'Edit instance',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.instances_page.switch_to_page()
        self.instances_page.click_query_row_by_name('Master')
        assert self.instances_page.find_instance_name_textbox().is_enabled()
        assert self.instances_page.find_instance_hostname_textbox().is_enabled()
        assert self.instances_page.get_save_button().is_enabled()
        self.instances_page.get_save_button().click()
