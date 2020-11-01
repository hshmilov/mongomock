import time

from services.adapters import stresstest_service, stresstest_scanner_service
from services.standalone_services.smtp_service import generate_random_valid_email, SmtpService
from ui_tests.pages.reports_page import ReportConfig, ReportFrequency
from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase
from test_credentials.test_gui_credentials import DEFAULT_USER

# pylint: disable=no-member


class TestReportsPermissions(PermissionsTestBase):
    DATA_QUERY = 'specific_data.data.name == regex(\' no\', \'i\')'

    TEST_REPORT_READ_ONLY_QUERY = 'query for read only test'
    TEST_REPORT_READ_ONLY_NAME = 'report name read only'
    TEST_REPORT_NO_DASHBOARD_NAME = 'report no dashboard'
    TEST_REPORT_CAN_ADD_NAME = 'report name can add'
    TEST_REPORT_CAN_EDIT_NAME = 'report name can EDIT'
    TEST_PRIVATE_ADMIN_REPORT = 'Private report - ADMIN user'
    TEST_PRIVATE_RESTRICTED_REPORT = 'Private report - RESTRICTED user'

    TEST_USERS_QUERY = 'query for users'
    ONLY_REPORTS_USER = 'only_reports'
    REPORT_SUBJECT = 'axonius read only report subject'

    def test_report_permissions(self):
        print('starting test_report_permissions')
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
        self._test_reports_with_add_permission()

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

    def test_reports_without_dashboard_permissions(self):
        print('starting test_reports_without_dashboard_permissions')
        self.reports_page.switch_to_page()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        self.settings_page.create_new_user_with_new_permission(self.ONLY_REPORTS_USER,
                                                               ui_consts.NEW_PASSWORD,
                                                               ui_consts.FIRST_NAME,
                                                               ui_consts.LAST_NAME,
                                                               self.settings_page.ONLY_REPORTS_PERMISSIONS)
        self.reports_page.switch_to_page()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_NO_DASHBOARD_NAME,
                                                     add_dashboard=True, spaces=['Axonius Dashboard']))
        self.reports_page.wait_for_table_to_load()
        self.login_page.switch_user(self.ONLY_REPORTS_USER, ui_consts.NEW_PASSWORD, '/reports')
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_report(self.TEST_REPORT_NO_DASHBOARD_NAME)
        self.reports_page.wait_for_spinner_to_end()
        assert self.reports_page.is_private_report_checkbox_disabled()
        assert self.reports_page.is_dashboard_checkbox_disabled()
        self.reports_page.click_save()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login()
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_report(self.TEST_REPORT_NO_DASHBOARD_NAME)
        assert not self.reports_page.is_dashboard_checkbox_disabled()
        assert self.reports_page.is_private_report_checkbox_disabled()
        assert self.reports_page.is_include_dashboard()

    def test_reports_entities_permissions(self):
        print('starting test_reports_entities_permissions')
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
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_new_report()
        assert self.reports_page.is_private_report_checkbox_disabled()
        assert self.reports_page.is_saved_queries_disabled()

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

    def test_private_report_permissions(self):
        print('starting test_private_report_permissions')
        self.reports_page.switch_to_page()
        # Admin user
        assert not self.reports_page.is_disabled_new_report_button()
        self.reports_page.click_new_report()
        self.reports_page.wait_for_spinner_to_end()
        assert not self.reports_page.is_private_report_checkbox_disabled()
        assert not self.reports_page.is_dashboard_checkbox_disabled()
        assert not self.reports_page.is_include_saved_queries_checkbox_disabled()
        self.reports_page.click_include_dashboard()
        self.reports_page.click_spaces_select()
        assert self.driver.find_element_by_xpath(self.reports_page.AXONIUS_DASHBOARD_SELECTOR_XPATH)
        assert len(self.driver.find_elements_by_css_selector(self.reports_page.SPACES_DROP_DOWN_CSS)) == 1
        self.reports_page.click_private_report()
        self.reports_page.click_spaces_select()
        assert self.driver.find_element_by_xpath(self.reports_page.MY_DASHBOARD_SELECTOR_XPATH)
        assert len(self.driver.find_elements_by_css_selector(self.reports_page.SPACES_DROP_DOWN_CSS)) == 2
        self.reports_page.click_private_report()
        time.sleep(2)
        self.reports_page.find_element_by_xpath(self.reports_page.SET_PUBLIC_MODAL_BUTTON_XPATH).click()
        time.sleep(2)
        self.reports_page.click_spaces_select()
        assert self.driver.find_element_by_xpath(self.reports_page.AXONIUS_DASHBOARD_SELECTOR_XPATH)
        assert len(self.driver.find_elements_by_css_selector(self.reports_page.SPACES_DROP_DOWN_CSS)) == 1
        self.reports_page.switch_to_page()

        # restricted user with only 'private' permission
        self.reports_page.click_new_report()
        self.reports_page.wait_for_spinner_to_end()
        # Create Public report
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_CAN_ADD_NAME,
                                                     add_dashboard=True, queries=None))
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        # Create Private report
        self.reports_page.click_new_report()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_PRIVATE_ADMIN_REPORT,
                                                     add_dashboard=True, queries=None, private=True))

        self._test_reports_with_private_permission()

    def _test_reports_with_private_permission(self):
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        settings_permissions = {
            'reports': [
                'Use private reports'
            ]
        }
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'reports',
                                                     'Use private reports',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        # User with Private only permission check
        assert not self.reports_page.is_disabled_new_report_button()
        assert self.reports_page.get_report_count() == 0
        self.reports_page.click_new_report()
        assert self.reports_page.is_private_report_checkbox_disabled()
        assert self.reports_page.is_private_report_checked()
        assert not self.reports_page.is_dashboard_checkbox_disabled()
        assert not self.reports_page.is_include_saved_queries_checkbox_disabled()
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        # Create Private report - for Restricted user
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_PRIVATE_RESTRICTED_REPORT,
                                                     add_dashboard=True, queries=None, private=True))
        self.reports_page.wait_for_table_to_load()
        assert self.reports_page.get_report_count() == 1
        self.reports_page.click_report(self.TEST_PRIVATE_RESTRICTED_REPORT)
        assert self.reports_page.is_private_report_checkbox_disabled()
        assert self.reports_page.is_private_report_checked()
        assert not self.reports_page.is_form_disabled()
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()

        # Restricted user with view permission
        self._test_private_reports_with_view_permission(user_role)

    def _test_private_reports_with_view_permission(self, user_role):
        settings_permissions = {
            'reports': [
                'View reports'
            ]
        }
        self.login_page.switch_user(DEFAULT_USER['user_name'], DEFAULT_USER['password'])
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert not self.reports_page.report_is_selectable(self.TEST_REPORT_CAN_ADD_NAME)
        assert self.reports_page.report_is_selectable(self.TEST_PRIVATE_RESTRICTED_REPORT)
        self.reports_page.click_report(self.TEST_REPORT_CAN_ADD_NAME)
        assert self.reports_page.is_private_report_checkbox_disabled()
        assert not self.reports_page.is_private_report_checked()
        assert self.reports_page.is_form_disabled()
        assert self.reports_page.is_save_button_disabled()
        assert not self.reports_page.is_download_report_disabled()
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_report(self.TEST_PRIVATE_RESTRICTED_REPORT)
        assert self.reports_page.is_private_report_checkbox_disabled()
        assert self.reports_page.is_private_report_checked()
        assert not self.reports_page.is_form_disabled()
        assert not self.reports_page.is_save_button_disabled()
        assert not self.reports_page.is_download_report_disabled()
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        # Restricted user can delete only private report
        assert not self.reports_page.is_row_checkbox_absent()
        self.reports_page.click_row_checkbox()
        self.reports_page.click_remove_reports(True)
        self.reports_page.wait_for_table_to_load()
        assert self.reports_page.get_report_count() == 1

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
        assert self.reports_page.is_private_report_checkbox_disabled()
        self.reports_page.click_save()

    def _test_reports_with_add_permission(self):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert not self.reports_page.is_disabled_new_report_button()
        assert self.reports_page.is_row_checkbox_absent()
        self.reports_page.click_new_report()
        self.reports_page.wait_for_spinner_to_end()
        assert self.reports_page.is_saved_queries_disabled()
        assert self.reports_page.is_private_report_checkbox_disabled()
        self.reports_page.switch_to_page()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_CAN_ADD_NAME,
                                                     add_dashboard=True, queries=None))
        self.reports_page.click_report(self.TEST_REPORT_CAN_ADD_NAME)
        assert self.reports_page.is_form_disabled()
        assert self.reports_page.is_save_button_disabled()
        assert self.reports_page.is_private_report_checkbox_disabled()

    def _test_reports_with_only_view_permission(self, settings_permissions, user_role):
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert self.reports_page.is_disabled_new_report_button()
        assert self.reports_page.is_row_checkbox_absent()
        self.reports_page.click_report(self.TEST_REPORT_READ_ONLY_NAME)
        assert self.reports_page.is_form_disabled()
        assert self.reports_page.is_save_button_disabled()
        assert self.reports_page.is_private_report_checkbox_disabled()

    def test_new_read_only_user_for_reports(self):
        print('starting test_new_read_only_user_for_reports')
        smtp_service = SmtpService()
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with smtp_service.contextmanager(take_ownership=True, retry_if_fail=True), \
                stress.contextmanager(take_ownership=True),\
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
            self.reports_page.wait_for_table_to_be_responsive()
            self.reports_page.is_disabled_new_report_button()
            self.reports_page.click_report(self.TEST_REPORT_READ_ONLY_NAME)
            self.reports_page.wait_for_spinner_to_end()

            assert self.reports_page.is_form_disabled()
