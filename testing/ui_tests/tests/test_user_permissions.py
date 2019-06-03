import pytest

from selenium.common.exceptions import NoSuchElementException

from services.adapters import stresstest_service, stresstest_scanner_service
from services.standalone_services.smtp_server import SMTPService, generate_random_valid_email
from ui_tests.pages.reports_page import ReportFrequency
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase


class TestUserPermissions(TestBase):
    REPORT_SUBJECT = 'axonius read only report subject'
    TEST_REPORT_READ_ONLY_QUERY = 'query for read only test'
    TEST_REPORT_READ_ONLY_NAME = 'report name read only'

    def test_new_user_is_restricted(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=ui_consts.NEW_PASSWORD)
        for screen in self.get_all_screens():
            screen.assert_screen_is_restricted()

    def test_new_read_only_user(self):
        self.settings_page.switch_to_page()

        # to fill up devices and users
        self.base_page.run_discovery()

        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME)

        self.settings_page.wait_for_user_created_toaster()

        for label in self.settings_page.get_permission_labels():
            self.settings_page.select_permissions(label, self.settings_page.READ_ONLY_PERMISSION)

        self.settings_page.click_save_manage_users_settings()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=ui_consts.NEW_PASSWORD)

        for screen in self.get_all_screens():
            with pytest.raises(NoSuchElementException):
                screen.assert_screen_is_restricted()

        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter('Microsoft Active Directory (AD)')
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
            self.devices_page.add_new_tag(ui_consts.TAG_NAME)

        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_load()
        self.users_page.click_row()
        with pytest.raises(NoSuchElementException):
            self.devices_page.add_new_tag(ui_consts.TAG_NAME)

        self.instances_page.switch_to_page()
        self.instances_page.wait_for_table_to_load()
        assert self.instances_page.is_connect_node_disabled()

    def test_user_restricted_entity(self):
        self.settings_page.switch_to_page()

        # to fill up devices and users
        self.base_page.run_discovery()

        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_ENTITY_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME)

        self.settings_page.wait_for_user_created_toaster()
        self.settings_page.select_permissions('Devices', self.settings_page.READ_ONLY_PERMISSION)
        self.settings_page.click_save_manage_users_settings()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_ENTITY_USERNAME, password=ui_consts.NEW_PASSWORD)

        self.users_page.assert_screen_is_restricted()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_column_data(self.devices_page.FIELD_ASSET_NAME))

    def test_new_user_validation(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.click_new_user()
        assert self.settings_page.find_disabled_create_user()
        self.settings_page.fill_new_user_details(ui_consts.RESTRICTED_USERNAME, '')
        assert self.settings_page.find_disabled_create_user()
        self.settings_page.fill_new_user_details(ui_consts.RESTRICTED_USERNAME, '', first_name=ui_consts.FIRST_NAME)
        assert self.settings_page.find_disabled_create_user()
        assert self.settings_page.find_password_input().get_attribute('class') == 'error-border'
        self.settings_page.fill_new_user_details(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        assert self.settings_page.find_password_input().get_attribute('class') == ''
        self.settings_page.click_create_user()

    def test_new_user_change_password(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME)

        self.settings_page.wait_for_user_created_toaster()

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
        self.settings_page.click_remove_user()
        self.settings_page.click_confirm_remove_user()

        self.settings_page.wait_for_user_removed_toaster()
        usernames = list(self.settings_page.get_all_users_from_users_and_roles())
        assert ui_consts.RESTRICTED_USERNAME not in usernames

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=self.password)
        assert self.login_page.wait_for_invalid_login_message()

    def test_user_roles(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.click_roles_button()
        self.settings_page.assert_default_role_is_restricted()
        self.settings_page.assert_placeholder_is_new()

        self.settings_page.select_role(self.settings_page.READ_ONLY_ROLE)
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.READ_ONLY_PERMISSION

        self.settings_page.select_role(self.settings_page.RESTRICTED_ROLE)
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.RESTRICTED_PERMISSION

        role_name = 'lalala'
        self.settings_page.select_role(self.settings_page.READ_ONLY_ROLE)
        self.settings_page.fill_role_name(role_name)
        self.settings_page.save_role()
        self.settings_page.click_done()
        self.settings_page.wait_for_role_saved_toaster()

        self.settings_page.click_roles_button()
        self.settings_page.select_role(self.settings_page.RESTRICTED_ROLE)
        self.settings_page.select_role(role_name)
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.READ_ONLY_PERMISSION
        self.settings_page.remove_role()
        self.settings_page.click_done()
        self.settings_page.wait_for_role_removed_toaster()

    def test_new_read_only_user_for_reports(self):
        smtp_service = SMTPService()
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

            data_query = 'specific_data.data.name == regex(\' no\', \'i\')'
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(data_query)
            self.devices_page.enter_search()
            self.devices_page.click_save_query()
            self.devices_page.fill_query_name(self.TEST_REPORT_READ_ONLY_QUERY)
            self.devices_page.click_save_query_save_button()
            self.devices_page.wait_for_table_to_load()
            recipient = generate_random_valid_email()
            queries = [{'entity': 'Devices', 'name': self.TEST_REPORT_READ_ONLY_QUERY}]
            self.reports_page.create_report(report_name=self.TEST_REPORT_READ_ONLY_NAME, add_dashboard=True,
                                            queries=queries, add_scheduling=True, email_subject=self.REPORT_SUBJECT,
                                            emails=[recipient], period=ReportFrequency.weekly)
            self.reports_page.wait_for_table_to_load()

            # to fill up devices and users
            self.base_page.run_discovery()

            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()
            self.settings_page.create_new_user(ui_consts.READ_ONLY_USERNAME,
                                               ui_consts.NEW_PASSWORD,
                                               ui_consts.FIRST_NAME,
                                               ui_consts.LAST_NAME)

            self.settings_page.wait_for_user_created_toaster()

            for label in self.settings_page.get_permission_labels():
                self.settings_page.select_permissions(label, self.settings_page.READ_ONLY_PERMISSION)

            self.settings_page.click_save_manage_users_settings()

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=ui_consts.READ_ONLY_USERNAME, password=ui_consts.NEW_PASSWORD)

            self.reports_page.switch_to_page()
            self.reports_page.is_disabled_new_report_button()
            self.reports_page.click_report(self.TEST_REPORT_READ_ONLY_NAME)
            self.reports_page.wait_for_spinner_to_end()

            assert self.reports_page.is_form_disabled()

    def test_new_user_with_role(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.RESTRICTED_ROLE)
        self.settings_page.wait_for_user_created_toaster()
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.RESTRICTED_PERMISSION
        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.RESTRICTED_PERMISSION

        # Change to Read Only role, save the user and check permissions correct also after refresh
        self.settings_page.select_user_role(self.settings_page.READ_ONLY_ROLE)
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.READ_ONLY_PERMISSION
        self.settings_page.click_save_manage_users_settings()
        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.READ_ONLY_PERMISSION

        self.settings_page.remove_user()
        # Create user with Read Only role and check permissions correct also after refresh
        self.settings_page.create_new_user(ui_consts.READ_ONLY_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.READ_ONLY_ROLE)
        self.settings_page.wait_for_user_created_toaster()
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.READ_ONLY_PERMISSION
        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.READ_ONLY_PERMISSION

        # Change to Read Only role, save the user and check permissions correct also after refresh
        self.settings_page.select_user_role(self.settings_page.RESTRICTED_ROLE)
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.RESTRICTED_PERMISSION
        self.settings_page.click_save_manage_users_settings()
        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        for label in self.settings_page.get_permission_labels():
            assert self.settings_page.get_permissions_text(label) == self.settings_page.RESTRICTED_PERMISSION
