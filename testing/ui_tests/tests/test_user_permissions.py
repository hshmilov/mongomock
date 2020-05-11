import pytest
from selenium.common.exceptions import NoSuchElementException

from test_credentials.test_gui_credentials import AXONIUS_RO_USER
from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase


# pylint: disable=no-member


class TestUserPermissions(PermissionsTestBase):
    DATA_QUERY = 'specific_data.data.name == regex(\' no\', \'i\')'

    def test_axonius_ro_user(self):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=AXONIUS_RO_USER['user_name'], password=AXONIUS_RO_USER['password'])
        for screen in self.get_all_screens():
            assert not screen.is_switch_button_disabled()

    def test_new_read_only_user(self):
        self.settings_page.switch_to_page()
        # to fill up devices and users
        self.base_page.run_discovery()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        self.settings_page.create_new_user_with_new_permission(ui_consts.RESTRICTED_USERNAME,
                                                               ui_consts.NEW_PASSWORD,
                                                               ui_consts.FIRST_NAME,
                                                               ui_consts.LAST_NAME,
                                                               self.settings_page.VIEWER_PERMISSIONS)
        self.settings_page.wait_for_user_created_toaster()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=ui_consts.NEW_PASSWORD)

        for screen in self.get_all_screens():
            assert not screen.is_switch_button_disabled()
            screen.switch_to_page()

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

    def test_user_restricted_entity(self):
        self.settings_page.switch_to_page()

        # to fill up devices and users
        self.base_page.run_discovery()

        self.settings_page.create_new_user_with_new_permission(ui_consts.RESTRICTED_ENTITY_USERNAME,
                                                               ui_consts.NEW_PASSWORD,
                                                               ui_consts.FIRST_NAME,
                                                               ui_consts.LAST_NAME,
                                                               {
                                                                   'devices_assets': [
                                                                       'View devices',
                                                                   ]
                                                               })

        self.login_page.switch_user(ui_consts.RESTRICTED_ENTITY_USERNAME, ui_consts.NEW_PASSWORD)

        self.users_page.assert_screen_is_restricted()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_column_data_slicer(self.devices_page.FIELD_ASSET_NAME))

    def test_new_user_validation(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.click_new_user()
        self.settings_page.wait_for_new_user_panel()
        self.settings_page.click_create_user()
        self.settings_page.assert_create_user_disabled()
        self.settings_page.fill_new_user_details(ui_consts.RESTRICTED_USERNAME, '')
        self.settings_page.assert_create_user_disabled()
        self.settings_page.fill_new_user_details(ui_consts.RESTRICTED_USERNAME, '', first_name=ui_consts.FIRST_NAME)
        self.settings_page.assert_create_user_disabled()
        assert self.settings_page.find_password_item().find_element_by_css_selector('.error-input')
        self.settings_page.fill_new_user_details(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        assert len(self.settings_page.find_password_item().find_elements_by_css_selector('.error-input')) == 0
        self.settings_page.assert_create_user_disabled()
        assert self.settings_page.find_role_item().find_element_by_css_selector('.error-input')
        self.settings_page.select_role(self.settings_page.RESTRICTED_ROLE)
        assert len(self.settings_page.find_role_item().find_elements_by_css_selector('.error-input')) == 0
        self.settings_page.click_create_user()

    def test_new_user_change_password(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.RESTRICTED_ROLE)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=ui_consts.NEW_PASSWORD)

        self.my_account_page.switch_to_page()
        self.my_account_page.change_password(
            ui_consts.NEW_PASSWORD,
            self.password,
            self.password,
            self.my_account_page.wait_for_password_changed_toaster)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=self.password)
        self.my_account_page.switch_to_page()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=self.password)
        self.settings_page.switch_to_page()

        self.settings_page.click_manage_users_settings()
        self.settings_page.wait_for_table_to_load()
        self.settings_page.remove_user_by_user_name_with_user_panel(ui_consts.RESTRICTED_USERNAME)
        self.settings_page.wait_for_table_to_load()

        usernames = list(self.settings_page.get_all_user_names())
        assert ui_consts.RESTRICTED_USERNAME not in usernames

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=self.password)
        assert self.login_page.wait_for_invalid_login_message()
