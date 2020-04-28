import pytest
from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until
from services.adapters import stresstest_service, stresstest_scanner_service
from services.standalone_services.smtp_service import SmtpService, generate_random_valid_email
from test_credentials.test_gui_credentials import AXONIUS_RO_USER, AXONIUS_USER
from ui_tests.pages.reports_page import ReportFrequency, ReportConfig
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_consts import JSON_ADAPTER_NAME
from ui_tests.tests.ui_test_base import TestBase

# pylint: disable=no-member


class TestUserPermissions(TestBase):
    REPORT_SUBJECT = 'axonius read only report subject'
    DATA_QUERY = 'specific_data.data.name == regex(\' no\', \'i\')'

    TEST_REPORT_READ_ONLY_QUERY = 'query for read only test'
    TEST_REPORT_READ_ONLY_NAME = 'report name read only'

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
            self.login_page.assert_screen_url_is_restricted(screen)

        self.settings_page.assert_screen_is_restricted()
        self.login_page.assert_screen_url_is_restricted(self.settings_page)

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

    def test_cloud_compliance_permissions(self):
        self.devices_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        cloud_visible_toggle = self.settings_page.find_checkbox_by_label('Cloud Visible')
        self.settings_page.click_toggle_button(cloud_visible_toggle, make_yes=True)
        cloud_enabled_toggle = self.settings_page.find_checkbox_by_label('Cloud Enabled')
        self.settings_page.click_toggle_button(cloud_enabled_toggle, make_yes=True)
        self.settings_page.save_and_wait_for_toaster()
        self.settings_page.click_manage_users_settings()
        self.compliance_page.switch_to_page()
        self.compliance_page.wait_for_table_to_load()
        self.compliance_page.assert_default_compliance_roles()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)

        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, password=ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.compliance_page.assert_screen_is_restricted()
        settings_permissions = {}
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'compliance',
                                                     'View Cloud Asset Compliance',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.compliance_page.switch_to_page()
        self.compliance_page.wait_for_table_to_load()
        self.compliance_page.assert_default_compliance_roles()
