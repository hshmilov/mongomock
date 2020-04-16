import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from axonius.consts.gui_consts import DASHBOARD_SPACE_PERSONAL
from axonius.utils.wait import wait_until
from services.adapters import stresstest_service, stresstest_scanner_service
from services.standalone_services.smtp_service import SmtpService, generate_random_valid_email
from test_credentials.test_gui_credentials import AXONIUS_RO_USER
from ui_tests.pages.reports_page import ReportFrequency, ReportConfig
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import JSON_ADAPTER_NAME, MANAGED_DEVICES_QUERY_NAME, EmailSettings

# pylint: disable=no-member,too-many-lines


class TestUserPermissions(TestBase):
    REPORT_SUBJECT = 'axonius read only report subject'
    DATA_QUERY = 'specific_data.data.name == regex(\' no\', \'i\')'

    TEST_REPORT_READ_ONLY_QUERY = 'query for read only test'
    TEST_REPORT_READ_ONLY_NAME = 'report name read only'
    TEST_REPORT_CAN_ADD_NAME = 'report name can add'
    TEST_REPORT_CAN_EDIT_NAME = 'report name can EDIT'

    TEST_USERS_QUERY = 'query for users'

    TEST_EMPTY_TITLE = 'test empty'
    OSX_OPERATING_SYSTEM_NAME = 'OS X Operating System'
    OSX_OPERATING_SYSTEM_FILTER = 'specific_data.data.os.type == "OS X"'
    DASHBOARD_EXACT_SEARCH_TERM = 'TestDomain'

    TEST_SPACE_NAME = 'test space'
    TEST_SPACE_NAME_RENAME = 'test rename'
    TEST_RENAME_SPACE_NAME = 'rename space'
    NOTE_TEXT = 'note text'
    TAG_NAME = 'test tag'

    CUSTOM_DEVICES_QUERY_SAVE_NAME = 'custom devices query'
    CUSTOM_DEVICES_NEW_QUERY_SAVE_NAME = 'custom new devices query'
    CUSTOM_USERS_QUERY_SAVE_NAME = 'custom users query'
    CUSTOM_NEW_USERS_SAVE_NAME = 'custom new users query'

    def test_new_user_is_restricted(self):
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
        for screen in self.get_all_screens():
            screen.assert_screen_is_restricted()

        self.settings_page.assert_screen_is_restricted()

    def test_axonius_ro_user(self):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=AXONIUS_RO_USER['user_name'], password=AXONIUS_RO_USER['password'])
        for screen in self.get_all_screens():
            with pytest.raises(NoSuchElementException):
                screen.assert_screen_is_restricted()

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
            with pytest.raises(NoSuchElementException):
                screen.assert_screen_is_restricted()

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

    def test_user_roles(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        # Checking that the viewer and restricted roles has the right permissions
        assert self.settings_page.match_role_permissions(self.settings_page.VIEWER_ROLE,
                                                         self.settings_page.VIEWER_PERMISSIONS)

        assert self.settings_page.match_role_permissions(self.settings_page.RESTRICTED_ROLE,
                                                         self.settings_page.RESTRICTED_PERMISSIONS)
        self.settings_page.wait_for_table_to_load()
        role_name = 'lalala'
        self.settings_page.click_new_role()
        self.settings_page.wait_for_role_panel_present()
        self.settings_page.fill_role_name(role_name)
        self.settings_page.click_create_role()
        self.settings_page.wait_for_role_successfully_created_toaster()
        # test delete role is missing
        self.settings_page.click_role_by_name(self.settings_page.RESTRICTED_ROLE)
        self.settings_page.wait_for_role_panel_present()
        self.settings_page.assert_role_remove_button_missing()
        self.settings_page.close_role_panel()
        # test the default permissions are the same as a restricted role
        assert self.settings_page.match_role_permissions(role_name,
                                                         self.settings_page.RESTRICTED_PERMISSIONS)
        # test delete role
        self.settings_page.remove_role(role_name)

    def test_new_read_only_user_for_reports(self):
        smtp_service = SmtpService()
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with smtp_service.contextmanager(take_ownership=True), stress.contextmanager(take_ownership=True), \
                stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)
            self.base_page.run_discovery()
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_send_emails_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)
            self.settings_page.fill_email_host(smtp_service.fqdn)
            self.settings_page.fill_email_port(smtp_service.port)
            self.settings_page.save_and_wait_for_toaster()

            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(self.DATA_QUERY)
            self.devices_page.enter_search()
            self.devices_page.click_save_query()
            self.devices_page.fill_query_name(self.TEST_REPORT_READ_ONLY_QUERY)
            self.devices_page.click_save_query_save_button()
            self.devices_page.wait_for_table_to_load()
            recipient = generate_random_valid_email()
            queries = [{'entity': 'Devices', 'name': self.TEST_REPORT_READ_ONLY_QUERY}]
            self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_READ_ONLY_NAME,
                                                         add_dashboard=True, queries=queries, add_scheduling=True,
                                                         email_subject=self.REPORT_SUBJECT,
                                                         emails=[recipient], period=ReportFrequency.weekly))
            self.reports_page.wait_for_table_to_load()

            # to fill up devices and users
            self.base_page.run_discovery()

            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()
            self.settings_page.create_new_user(ui_consts.READ_ONLY_USERNAME,
                                               ui_consts.NEW_PASSWORD,
                                               ui_consts.FIRST_NAME,
                                               ui_consts.LAST_NAME,
                                               self.settings_page.VIEWER_ROLE)

            self.settings_page.wait_for_user_created_toaster()

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=ui_consts.READ_ONLY_USERNAME, password=ui_consts.NEW_PASSWORD)

            self.reports_page.switch_to_page()
            self.reports_page.is_disabled_new_report_button()
            self.reports_page.click_report(self.TEST_REPORT_READ_ONLY_NAME)
            self.reports_page.wait_for_spinner_to_end()

            assert self.reports_page.is_form_disabled()

    def _enter_user_management_and_create_restricted_user(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.RESTRICTED_ROLE)
        self.settings_page.wait_for_user_created_toaster()

    @pytest.mark.skip('AX-6970')
    def test_new_user_with_role(self):
        self._enter_user_management_and_create_restricted_user()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.RESTRICTED_USERNAME)
        assert self.settings_page.RESTRICTED_ROLE in user_data
        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.RESTRICTED_USERNAME)
        assert self.settings_page.RESTRICTED_ROLE in user_data

        self.settings_page.click_manage_roles_settings()
        self.settings_page.match_role_permissions(self.settings_page.RESTRICTED_ROLE,
                                                  self.settings_page.RESTRICTED_PERMISSIONS)

        self.settings_page.click_manage_users_settings()
        # Change to Read Only role, save the user and check permissions correct also after refresh
        self.settings_page.click_edit_user(ui_consts.RESTRICTED_USERNAME)
        self.settings_page.wait_for_new_user_panel()
        self.settings_page.select_role(self.settings_page.VIEWER_ROLE)
        self.settings_page.click_save_button()
        self.settings_page.wait_for_user_updated_toaster()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.RESTRICTED_USERNAME)
        assert self.settings_page.VIEWER_ROLE in user_data

        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.RESTRICTED_USERNAME)
        assert self.settings_page.VIEWER_ROLE in user_data

        self.settings_page.click_manage_roles_settings()
        self.settings_page.match_role_permissions(self.settings_page.VIEWER_ROLE,
                                                  self.settings_page.VIEWER_PERMISSIONS)

        self.settings_page.click_manage_users_settings()
        self.settings_page.remove_user_by_user_name_with_user_panel(ui_consts.RESTRICTED_USERNAME)
        # Create user with Read Only role and check permissions correct also after refresh
        self.settings_page.create_new_user(ui_consts.READ_ONLY_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.VIEWER_ROLE)
        self.settings_page.wait_for_user_created_toaster()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.READ_ONLY_USERNAME)
        assert self.settings_page.VIEWER_ROLE in user_data
        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.READ_ONLY_USERNAME)
        assert self.settings_page.VIEWER_ROLE in user_data

        # Change to Read Only role, save the user and check permissions correct also after refresh
        self.settings_page.click_edit_user(ui_consts.READ_ONLY_USERNAME)
        self.settings_page.wait_for_new_user_panel()
        self.settings_page.select_role(self.settings_page.RESTRICTED_ROLE)
        self.settings_page.click_save_button()
        self.settings_page.wait_for_user_updated_toaster()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.READ_ONLY_USERNAME)
        assert self.settings_page.RESTRICTED_ROLE in user_data
        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.READ_ONLY_USERNAME)
        assert self.settings_page.RESTRICTED_ROLE in user_data

    def test_user_predefined_role_duplicate_and_change(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                         ui_consts.NEW_PASSWORD,
                                                         ui_consts.FIRST_NAME,
                                                         ui_consts.LAST_NAME,
                                                         self.settings_page.RESTRICTED_ROLE)

        user = self.settings_page.get_user_object_by_user_name(ui_consts.RESTRICTED_USERNAME)

        self.settings_page.click_manage_roles_settings()

        assert user.role != self.settings_page.RESTRICTED_ROLE

        self.settings_page.click_role_by_name(user.role)
        self.settings_page.wait_for_side_panel()
        self.settings_page.get_role_edit_panel_action().click()

        self.settings_page.select_permissions({
            'devices_assets': [
                'View devices',
            ]
        })
        self.settings_page.click_save_button()
        self.settings_page.safeguard_click_confirm('Yes')
        self.settings_page.wait_for_role_successfully_saved_toaster()

    def test_settings_users_permissions(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.settings_page.assert_screen_is_restricted()
        self.login_page.logout_and_login_with_admin()
        self.settings_page.switch_to_page()
        settings_permissions = {'settings': []}
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'View system settings',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        assert not self.settings_page.assert_screen_is_restricted()
        self.settings_page.switch_to_page()
        assert not self.settings_page.is_users_and_roles_enabled()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'View user accounts and roles',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.settings_page.switch_to_page()
        assert self.settings_page.is_users_and_roles_enabled()
        self.settings_page.click_manage_users_settings()
        self.settings_page.assert_new_user_disabled()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Add user',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        new_user = 'test_user'
        self.settings_page.create_new_user(new_user,
                                           ui_consts.NEW_PASSWORD,
                                           new_user,
                                           new_user,
                                           self.settings_page.RESTRICTED_ROLE)
        # Checking the user can't click on any row
        assert len(self.settings_page.get_all_table_rows(clickable_rows=True)) == 0
        # Checking user can not be deleted
        self.settings_page.is_row_checkbox_absent(2)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Edit users',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.click_edit_user(new_user)
        self.settings_page.assert_user_remove_button_missing()
        self.settings_page.click_save_button()
        self.settings_page.wait_for_user_updated_toaster()

        update_user = 'update user'
        self.settings_page.update_new_user(new_user,
                                           ui_consts.UPDATE_PASSWORD,
                                           update_user,
                                           update_user,
                                           self.settings_page.VIEWER_ROLE)
        self.settings_page.wait_for_table_to_load()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Delete user',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        self.settings_page.remove_user_by_user_name_with_selection(new_user)

        self.settings_page.create_new_user(new_user,
                                           ui_consts.NEW_PASSWORD,
                                           new_user,
                                           new_user,
                                           self.settings_page.RESTRICTED_ROLE)

        self.settings_page.remove_user_by_user_name_with_user_panel(new_user)

    def _add_action_to_role_and_login_with_user(self, permissions, category, add_action, role, user_name, password):
        self.login_page.logout_and_login_with_admin()
        if not permissions.get(category):
            permissions[category] = []
        permissions[category].append(add_action)
        self.settings_page.update_role(role, permissions, True)
        self.login_page.logout_and_login_with_user(user_name, password=password)

    def test_settings_roles_permissions(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.settings_page.switch_to_page()

        settings_permissions = {'settings': []}
        settings_permissions['settings'].append('View system settings')
        settings_permissions['settings'].append('View user accounts and roles')

        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.settings_page.switch_to_page()
        assert self.settings_page.is_users_and_roles_enabled()
        self.settings_page.click_manage_roles_settings()
        self.settings_page.assert_new_role_disabled()
        self.settings_page.click_role_by_name(user_role)
        with pytest.raises(NoSuchElementException):
            self.settings_page.get_save_button()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Edit roles',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_settings_roles_with_edit_permission(user_role)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Add role',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        new_role_name = self._test_settings_roles_with_add_permission()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Delete roles',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_settings_roles_with_delete_permission(new_role_name)

    def _test_settings_roles_with_delete_permission(self, new_role_name):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        assert self.settings_page.get_new_role_enabled_button()
        self.settings_page.click_role_by_name(new_role_name)
        self.settings_page.wait_for_role_panel_present()
        self.settings_page.get_role_edit_panel_action().click()
        self.settings_page.click_save_button()
        self.settings_page.wait_for_role_panel_absent()
        self.settings_page.remove_role(new_role_name)

    def _test_settings_roles_with_add_permission(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        assert self.settings_page.get_new_role_enabled_button()
        self.settings_page.click_role_by_name(self.settings_page.RESTRICTED_ROLE)
        assert self.settings_page.get_role_duplicate_panel_action()
        self.settings_page.assert_role_remove_button_missing()
        self.settings_page.close_role_panel()
        new_role_name = 'new role'
        self.settings_page.create_new_role(new_role_name, self.settings_page.RESTRICTED_PERMISSIONS)
        self.settings_page.click_role_by_name(new_role_name)
        assert self.settings_page.get_role_duplicate_panel_action()
        self.settings_page.assert_role_remove_button_missing()
        self.settings_page.get_cancel_button().click()
        return new_role_name

    def _test_settings_roles_with_edit_permission(self, user_role):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        self.settings_page.assert_new_role_disabled()
        self.settings_page.click_role_by_name(user_role)
        self.settings_page.wait_for_side_panel()
        with pytest.raises(TimeoutException):
            self.settings_page.get_role_duplicate_panel_action()
        with pytest.raises(TimeoutException):
            self.settings_page.get_role_remove_panel_action()
        self.settings_page.get_role_edit_panel_action().click()
        self.settings_page.click_save_button()
        self.settings_page.safeguard_click_confirm('Yes')

    def test_settings_general_permissions(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.settings_page.switch_to_page()

        settings_permissions = {'settings': []}
        settings_permissions['settings'].append('View system settings')
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        assert self.base_page.is_run_research_disabled()
        self.account_page.switch_to_page()
        assert not self.account_page.is_reset_key_displayed()
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Reset API Key',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        assert self.base_page.is_run_research_disabled()
        self.account_page.switch_to_page()
        assert self.account_page.is_reset_key_displayed()
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Run manual discovery cycle',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        assert not self.base_page.is_run_research_disabled()

        self.settings_page.switch_to_page()
        self.settings_page.click_lifecycle_settings()
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.click_global_settings()
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.click_gui_settings()
        assert self.settings_page.is_save_button_disabled()
        self.account_page.switch_to_page()
        assert self.account_page.is_reset_key_displayed()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Update system settings',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.settings_page.switch_to_page()
        self.settings_page.click_lifecycle_settings()
        assert not self.settings_page.is_save_button_disabled()
        self.settings_page.click_global_settings()
        assert not self.settings_page.is_save_button_disabled()
        self.settings_page.click_gui_settings()
        assert not self.settings_page.is_save_button_disabled()
        self.account_page.switch_to_page()
        assert self.account_page.is_reset_key_displayed()
        assert not self.base_page.is_run_research_disabled()

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
                'View devices',
                'Run saved queries',
                'Create saved query',
            ]
        }

        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.is_missing_space(DASHBOARD_SPACE_PERSONAL)
        assert self.dashboard_page.is_new_chart_card_missing()
        self._test_chart_permissions(settings_permissions, user_role)
        self._test_spaces_permissions(settings_permissions, user_role)

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

    @pytest.mark.skip('AX-7052')
    def test_devices_permissions(self):
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
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_and_save(self.CUSTOM_DEVICES_QUERY_SAVE_NAME,
                                              self.devices_page.JSON_ADAPTER_FILTER)
        self.devices_page.refresh()
        self.devices_page.load_notes()
        self.devices_page.create_note(self.NOTE_TEXT)
        self.devices_page.click_tab(self.devices_page.FIELD_TAGS)
        self.devices_page.open_edit_tags()
        self.devices_page.create_save_tags([self.TAG_NAME])
        self.devices_page.wait_for_spinner_to_end()

        self.settings_page.switch_to_page()
        settings_permissions = {
            'devices_assets': [
                'View devices'
            ]
        }
        self._test_entities_with_only_view_permission(settings_permissions, user_role, self.devices_page)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'Edit devices',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_entities_with_edit_permission(self.devices_page)

    @pytest.mark.skip('AX-6987')
    def test_devices_saved_queries(self):
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
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_and_save(self.CUSTOM_DEVICES_QUERY_SAVE_NAME,
                                              self.devices_page.JSON_ADAPTER_FILTER)

        self.settings_page.switch_to_page()
        settings_permissions = {
            'devices_assets': [
                'View devices'
            ]
        }
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)

        self._test_saved_queries_without_any_permission(self.devices_page,
                                                        self.devices_queries_page,
                                                        self.CUSTOM_DEVICES_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'Run saved queries',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_run_permission(self.devices_page,
                                                     self.devices_queries_page,
                                                     self.CUSTOM_DEVICES_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'Edit saved queries',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_edit_permission(self.devices_page,
                                                      self.devices_queries_page,
                                                      self.CUSTOM_DEVICES_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'Create saved query',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_create_permission(self.devices_page, self.CUSTOM_DEVICES_NEW_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'Delete saved query',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_delete_permission(self.devices_page,
                                                        self.devices_queries_page,
                                                        self.CUSTOM_DEVICES_QUERY_SAVE_NAME,
                                                        self.CUSTOM_DEVICES_NEW_QUERY_SAVE_NAME)

    def test_users_permissions(self):
        self.users_page.switch_to_page()
        self.base_page.run_discovery()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)

        self.users_page.switch_to_page()
        self.users_page.refresh()
        self.users_page.load_notes()
        self.users_page.create_note(self.NOTE_TEXT)
        self.users_page.click_tab(self.devices_page.FIELD_TAGS)
        self.users_page.open_edit_tags()
        self.users_page.create_save_tags([self.TAG_NAME])
        self.users_page.wait_for_spinner_to_end()

        self.settings_page.switch_to_page()
        settings_permissions = {
            'users_assets': [
                'View users'
            ]
        }
        self._test_entities_with_only_view_permission(settings_permissions, user_role, self.users_page)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'Edit users',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_entities_with_edit_permission(self.users_page)

    def test_users_saved_queries(self):
        self.users_page.switch_to_page()
        self.base_page.run_discovery()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.users_page.switch_to_page()
        self.users_page.run_filter_and_save(self.CUSTOM_USERS_QUERY_SAVE_NAME,
                                            self.users_page.JSON_ADAPTER_FILTER)

        self.settings_page.switch_to_page()
        settings_permissions = {
            'users_assets': [
                'View users'
            ]
        }

        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)

        self._test_saved_queries_without_any_permission(self.users_page,
                                                        self.users_queries_page,
                                                        self.CUSTOM_USERS_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'Run saved queries',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_run_permission(self.users_page,
                                                     self.users_queries_page,
                                                     self.CUSTOM_USERS_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'Edit saved queries',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_edit_permission(self.users_page,
                                                      self.users_queries_page,
                                                      self.CUSTOM_USERS_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'Create saved query',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_create_permission(self.users_page, self.CUSTOM_NEW_USERS_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'Delete saved query',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_delete_permission(self.users_page,
                                                        self.users_queries_page,
                                                        self.CUSTOM_USERS_QUERY_SAVE_NAME,
                                                        self.CUSTOM_NEW_USERS_SAVE_NAME)

    def _test_entities_with_only_view_permission(self, settings_permissions, user_role, entities_page):
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        assert entities_page.is_row_checkbox_absent()
        assert entities_page.is_actions_button_absent()
        entities_page.load_notes()
        entities_page.assert_add_note_disabled()
        assert not entities_page.can_edit_notes()
        assert entities_page.is_row_checkbox_absent()
        entities_page.click_tab(entities_page.FIELD_TAGS)
        entities_page.assert_edit_tags_disabled()
        entities_page.assert_remove_tags_disabled()
        entities_page.click_adapters_tab()
        entities_page.click_custom_data_tab()
        assert entities_page.is_custom_data_edit_disabled()

    def _test_entities_with_edit_permission(self, entities_page):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        assert not entities_page.is_row_checkbox_absent()
        entities_page.click_row_checkbox()
        assert not entities_page.is_actions_button_absent()
        entities_page.click_row_checkbox()
        entities_page.load_notes()
        assert entities_page.get_add_note_button()
        entities_page.create_note(self.NOTE_TEXT)
        assert entities_page.can_edit_notes()
        assert not entities_page.is_row_checkbox_absent()
        entities_page.click_tab(entities_page.FIELD_TAGS)
        assert entities_page.get_edit_tags_button()
        assert entities_page.get_remove_tags_button()
        entities_page.click_adapters_tab()
        entities_page.click_custom_data_tab()
        assert entities_page.find_custom_data_edit()

    @staticmethod
    def _test_saved_queries_without_any_permission(entities_page, queries_page, query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()

        entities_page.check_search_list_for_absent_names([query_name])
        entities_page.fill_filter('cb')
        entities_page.enter_search()
        assert entities_page.is_query_save_disabled()
        queries_page.switch_to_page()
        queries_page.is_row_checkbox_absent()
        queries_page.click_query_row_by_name(query_name)
        queries_page.assert_run_query_disabled()
        with pytest.raises(TimeoutException):
            queries_page.get_edit_panel_action()
        with pytest.raises(TimeoutException):
            queries_page.get_remove_panel_action()

    @staticmethod
    def _test_saved_queries_with_run_permission(entities_page, queries_page, query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()

        entities_page.check_search_list_for_names([query_name])
        entities_page.execute_saved_query(query_name)
        assert entities_page.is_query_save_as_disabled()
        assert not entities_page.can_rename_query(query_name)
        queries_page.switch_to_page()
        queries_page.is_row_checkbox_absent()
        queries_page.click_query_row_by_name(query_name)
        with pytest.raises(TimeoutException):
            queries_page.get_edit_panel_action()
        with pytest.raises(TimeoutException):
            queries_page.get_remove_panel_action()
        queries_page.run_query()

    @staticmethod
    def _test_saved_queries_with_edit_permission(entities_page, queries_page, query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()

        entities_page.check_search_list_for_names([query_name])
        entities_page.execute_saved_query(query_name)
        assert entities_page.is_query_save_as_disabled()
        assert entities_page.can_rename_query(query_name)

        queries_page.switch_to_page()
        queries_page.is_row_checkbox_absent()
        queries_page.click_query_row_by_name(query_name)
        queries_page.wait_for_side_panel()
        queries_page.get_edit_panel_action().click()

        queries_page.click_save_changes()
        with pytest.raises(TimeoutException):
            queries_page.get_remove_panel_action()
        queries_page.run_query()

    def _test_saved_queries_with_create_permission(self, entities_page, query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        entities_page.fill_filter('cb')
        entities_page.enter_search()
        assert not entities_page.is_query_save_disabled()
        entities_page.run_filter_and_save(query_name, self.devices_page.JSON_ADAPTER_FILTER)

    @staticmethod
    def _test_saved_queries_with_delete_permission(entities_page, queries_page, query_name, new_query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()

        queries_page.switch_to_page()
        queries_page.check_query_by_name(query_name)
        queries_page.remove_selected_queries(True)
        queries_page.click_query_row_by_name(new_query_name)
        queries_page.get_remove_panel_action().click()
        queries_page.safeguard_click_confirm('Remove Saved Query')

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
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
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

    def test_adapters_permissions(self):
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
            'adapters': [
                'View adapters'
            ]
        }
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.assert_new_server_button_is_disabled()
        self.adapters_page.assert_advanced_settings_is_disabled()
        assert self.adapters_page.is_row_checkbox_absent()
        self.adapters_page.assert_servers_cant_be_opened()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'adapters',
                                                     'Add connection',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.adapters_page.switch_to_page()
        self.adapters_page.add_json_extra_client()
        assert self.adapters_page.is_row_checkbox_absent()
        self.adapters_page.assert_servers_cant_be_opened()
        self.adapters_page.assert_advanced_settings_is_disabled()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'adapters',
                                                     'Edit connections',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.assert_new_server_button_is_enabled()
        assert self.adapters_page.is_row_checkbox_absent()
        self.adapters_page.assert_advanced_settings_is_disabled()
        self.adapters_page.click_edit_server_by_name('Client1')
        self.adapters_page.click_save()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'adapters',
                                                     'Edit adapter advanced settings',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.assert_new_server_button_is_enabled()
        self.adapters_page.assert_advanced_settings_is_enabled()
        assert self.adapters_page.is_row_checkbox_absent()
        self.adapters_page.click_edit_server_by_name('Client1')
        wait_until(lambda: not self.adapters_page.is_save_button_disabled())
        self.adapters_page.click_save()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'adapters',
                                                     'Delete connection',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.assert_new_server_button_is_enabled()
        self.adapters_page.assert_advanced_settings_is_enabled()
        assert not self.adapters_page.is_row_checkbox_absent()
        self.adapters_page.click_edit_server()
        wait_until(lambda: not self.adapters_page.is_save_button_disabled())
        self.adapters_page.click_save()

    @pytest.mark.skip('AX-7052')
    def test_report_permissions(self):
        self.reports_page.switch_to_page()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.fill_filter(self.DATA_QUERY)
        self.devices_page.enter_search()
        self.devices_page.click_save_query()
        self.devices_page.fill_query_name(self.TEST_REPORT_READ_ONLY_QUERY)
        self.devices_page.click_save_query_save_button()
        self.devices_page.wait_for_table_to_load()
        device_queries = [{'entity': 'Devices', 'name': self.TEST_REPORT_READ_ONLY_QUERY}]

        self.reports_page.switch_to_page()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_READ_ONLY_NAME,
                                                     add_dashboard=True, queries=device_queries))
        self.reports_page.wait_for_table_to_load()
        settings_permissions = {
            'reports': [
                'View reports'
            ]
        }
        self._test_reports_with_only_view_permission(settings_permissions, user_role)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'reports',
                                                     'Add report',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_reports_with_add_permission(device_queries)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'reports',
                                                     'Edit reports',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_reports_with_edit_permissions()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'reports',
                                                     'Delete report',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_reports_with_delete_permission()

    def test_reports_entities_permissions(self):
        self.reports_page.switch_to_page()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.fill_filter(self.DATA_QUERY)
        self.devices_page.enter_search()
        self.devices_page.click_save_query()
        self.devices_page.fill_query_name(self.TEST_REPORT_READ_ONLY_QUERY)
        self.devices_page.click_save_query_save_button()
        self.devices_page.wait_for_table_to_load()
        device_queries = [{'entity': 'Devices', 'name': self.TEST_REPORT_READ_ONLY_QUERY}]

        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_load()
        self.users_page.fill_filter(self.DATA_QUERY)
        self.users_page.enter_search()
        self.users_page.click_save_query()
        self.users_page.fill_query_name(self.TEST_USERS_QUERY)
        self.users_page.click_save_query_save_button()
        self.users_page.wait_for_table_to_load()
        users_queries = [{'entity': 'Users', 'name': self.TEST_USERS_QUERY}]

        self.reports_page.switch_to_page()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_READ_ONLY_NAME,
                                                     add_dashboard=True, queries=device_queries))
        self.reports_page.wait_for_table_to_load()
        settings_permissions = {
            'reports': [
                'View reports',
                'Add report'
            ],
        }

        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_new_report()
        self.reports_page.click_include_queries()
        self.reports_page.assert_select_saved_views_is_empty(0)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'View devices',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.reports_page.switch_to_page()
        self.reports_page.click_new_report()
        self.reports_page.click_include_queries()
        for index, query in enumerate(device_queries):
            self.reports_page.select_saved_view_from_multiple(index, query['name'], query['entity'])
            if index < len(device_queries) - 1:
                self.reports_page.click_add_query()
            self.reports_page.click_add_query()
        assert self.reports_page.select_saved_view(self.TEST_USERS_QUERY, 'Users') is None

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'View users',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.reports_page.switch_to_page()
        self.reports_page.click_new_report()
        self.reports_page.click_include_queries()
        self.reports_page.select_saved_views(device_queries)
        self.reports_page.click_add_query()
        self.reports_page.select_saved_views(users_queries)

    def _test_reports_with_delete_permission(self):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert not self.reports_page.is_disabled_new_report_button()
        assert not self.reports_page.is_row_checkbox_absent()
        self.reports_page.click_row_checkbox()
        self.reports_page.click_remove_reports(True)

    def _test_reports_with_edit_permissions(self):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert not self.reports_page.is_disabled_new_report_button()
        assert self.reports_page.is_row_checkbox_absent()
        self.reports_page.click_report(self.TEST_REPORT_CAN_ADD_NAME)
        assert not self.reports_page.is_form_disabled()
        assert not self.reports_page.is_save_button_disabled()
        self.reports_page.click_save()

    def _test_reports_with_add_permission(self, queries):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert not self.reports_page.is_disabled_new_report_button()
        assert self.reports_page.is_row_checkbox_absent()
        with pytest.raises(AssertionError, match='Could not find option Devices'):
            self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_CAN_ADD_NAME,
                                                         add_dashboard=True, queries=queries))
        self.reports_page.close_dropdown()
        self.reports_page.switch_to_page()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_CAN_ADD_NAME,
                                                     add_dashboard=True, queries=None))
        self.reports_page.click_report(self.TEST_REPORT_CAN_ADD_NAME)
        assert self.reports_page.is_form_disabled()
        assert self.reports_page.is_save_button_disabled()

    def _test_reports_with_only_view_permission(self, settings_permissions, user_role):
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert self.reports_page.is_disabled_new_report_button()
        assert self.reports_page.is_row_checkbox_absent()
        self.reports_page.click_report(self.TEST_REPORT_READ_ONLY_NAME)
        assert self.reports_page.is_form_disabled()
        assert self.reports_page.is_save_button_disabled()

    def test_enforcements_permissions(self):
        self.settings_page.switch_to_page()
        self.settings_page.add_email_server(EmailSettings.host, EmailSettings.port)

        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)

        self.enforcements_page.switch_to_page()
        enforcement_name = 'test_empty_enforcement'
        enforcement_action_name = 'test_email_action'
        self.enforcements_page.create_basic_enforcement(enforcement_name, MANAGED_DEVICES_QUERY_NAME)
        recipient = generate_random_valid_email()
        self.enforcements_page.add_main_action_send_email(enforcement_action_name, recipient=recipient)

        self.enforcements_page.wait_for_table_to_load()
        settings_permissions = {
            'enforcements': [
                'View Enforcement Center'
            ],
            'devices_assets': [
                'View devices'
            ]
        }
        self._test_enforcements_with_only_view_permission(settings_permissions, user_role, enforcement_name)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'View Enforcement Tasks',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.enforcements_page.switch_to_page()
        assert not self.enforcements_page.is_view_tasks_button_disabled()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Add Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_enforcements_with_add_permission()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Delete Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_enforcements_with_delete_permission()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Edit Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_enforcements_with_edit_permission()

    def _test_enforcements_with_only_view_permission(self, settings_permissions, user_role, enforcement_name):
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.is_view_tasks_button_disabled()
        assert self.enforcements_page.is_disabled_new_enforcement_button()
        assert self.enforcements_page.is_row_checkbox_absent()
        self.enforcements_page.click_enforcement(enforcement_name)
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.get_save_button()

    def _test_enforcements_with_add_permission(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        assert not self.enforcements_page.is_disabled_new_enforcement_button()
        assert self.reports_page.is_row_checkbox_absent()
        new_enforcement_name = 'only add enforcement'
        new_enforcement_action_name = 'only add enforcement action'
        self.enforcements_page.create_basic_enforcement(new_enforcement_name, MANAGED_DEVICES_QUERY_NAME)
        recipient = generate_random_valid_email()
        self.enforcements_page.add_main_action_send_email(new_enforcement_action_name, recipient=recipient)

        self.enforcements_page.click_enforcement(new_enforcement_name)
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.get_save_button()

    def _test_enforcements_with_delete_permission(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        assert not self.enforcements_page.is_disabled_new_enforcement_button()
        assert not self.reports_page.is_row_checkbox_absent()
        new_enforcement_name = 'with delete enforcement'
        new_enforcement_action_name = 'with delete enforcement action'
        self.enforcements_page.create_basic_enforcement(new_enforcement_name, MANAGED_DEVICES_QUERY_NAME)
        recipient = generate_random_valid_email()
        self.enforcements_page.add_main_action_send_email(new_enforcement_action_name, recipient=recipient)

        self.enforcements_page.click_enforcement(new_enforcement_name)
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.get_save_button()

        self.enforcements_page.click_exit_button()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_select_enforcement(1)
        self.enforcements_page.remove_selected_enforcements(True)

    def _test_enforcements_with_edit_permission(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        assert not self.enforcements_page.is_disabled_new_enforcement_button()
        assert not self.reports_page.is_row_checkbox_absent()
        new_enforcement_name = 'with edit enforcement'
        new_enforcement_action_name = 'with edit enforcement action'
        self.enforcements_page.create_basic_enforcement(new_enforcement_name, MANAGED_DEVICES_QUERY_NAME)
        recipient = generate_random_valid_email()
        self.enforcements_page.add_main_action_send_email(new_enforcement_action_name, recipient=recipient)

        self.enforcements_page.click_enforcement(new_enforcement_name)
        self.enforcements_page.click_save_button()

        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_select_enforcement(2)
        self.enforcements_page.remove_selected_enforcements(True)
