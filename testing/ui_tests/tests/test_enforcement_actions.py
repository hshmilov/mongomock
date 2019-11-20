import datetime
import time
from typing import List
import pytest
from selenium.common.exceptions import NoSuchElementException

import boto3
from flaky import flaky
from retrying import retry

from axonius.consts.system_consts import AXONIUS_DNS_SUFFIX
from axonius.utils.wait import wait_until
from axonius.utils.parsing import make_dict_from_csv
from services.adapters import stresstest_scanner_service, stresstest_service
from services.standalone_services.smtp_server import generate_random_valid_email
from services.standalone_services.maildiranasaurus_server import MailDiranasaurusService as SMTPService
from services.standalone_services.syslog_server import SyslogService
from test_helpers.log_tester import LogTester
from ui_tests.tests.ui_consts import Enforcements, REPORTS_LOG_PATH
from ui_tests.tests.ui_test_base import TestBase
from test_credentials.json_file_credentials import client_details as json_file_creds
from test_credentials.test_aws_credentials import EC2_ECS_EKS_READONLY_ACCESS_KEY_ID, \
    EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY

ENFORCEMENT_NAME = 'Special enforcement name'
COMMON_ENFORCEMENT_QUERY = 'Enabled AD Devices'
ENFORCEMENT_CHANGE_NAME = 'test_enforcement_change'
ENFORCEMENT_TEST_NAME_1 = 'Test_enforcement_1'
ENFORCEMENT_TEST_NAME_2 = 'Test_enforcement_2'
ENFORCEMENT_TEST_NAME_3 = 'Test_enforcement_3'

SAVED_QUERY_JUST_CBR_NAME = 'just_cbr'
SAVED_QUERY_JUST_CBR = 'adapters == \'carbonblack_response_adapter\''
AD_LAST_OR_ADDED_QUERY = '({added_filter}) or adapters_data.active_directory_adapter.ad_last_logon> date("NOW-8d")'

CUSTOM_TAG = 'superTag'
TAG_ALL_COMMENT = 'tag all'
TAG_NEW_COMMENT = 'tag new'

JSON_ADAPTER_NAME = 'JSON File'
AXONIUS_CI_TESTS_BUCKET = 'axonius-ci-tests'


def create_enforcement_name(number, enforcement_name=ENFORCEMENT_NAME):
    return f'{enforcement_name} {number}'


@retry(stop_max_attempt_number=5 * 60, wait_fixed=1000)
def _verify_in_syslog_data(syslog_service: SyslogService, text):
    last_log = list(syslog_service.get_syslog_data())[-100:]
    assert any(bytes(text, 'ascii') in l for l in last_log)


class TestEnforcementActions(TestBase):
    DATA_QUERY = 'specific_data.data.name == regex(\'avigdor no\', \'i\')'

    def _create_notifications(self, count=1) -> List[str]:
        enforcement_names = [create_enforcement_name(i) for i in range(count)]
        for name in enforcement_names:
            self.enforcements_page.create_notifying_enforcement(name, COMMON_ENFORCEMENT_QUERY,
                                                                False, False)
        self.base_page.run_discovery()

        # It's easier to delete the notifications from the DB
        self.axonius_system.get_enforcements_db().delete_many({'name': {
            '$in': enforcement_names
        }})
        self.axonius_system.get_actions_db().delete_many({'name': {
            '$in': enforcement_names
        }})
        return enforcement_names

    def test_notification_sanity(self):
        self._create_notifications(2)

        self.notification_page.wait_for_count(2)

        # Double click to open and close
        self.notification_page.click_notification_peek()
        self.notification_page.click_notification_peek()

        self.notification_page.wait_for_count(0, 'Notification expected to be zeroed After clicking on peek')

        assert len(self.notification_page.get_peek_notifications()) == 2

        self.notification_page.click_notification_peek()
        self.notification_page.click_view_notifications()

        assert not self.notification_page.is_peek_open(), \
            'Notification peek should be close after clicking "View All"'

    def test_notification_peek_count(self):
        """ test that when we add more 6 notifications, we get only 6 in notification peek"""
        self._create_notifications(7)
        self.notification_page.wait_for_count(7)

        assert len(self.notification_page.get_peek_notifications()) == 6

    def test_single_notification(self):
        notification_name = self._create_notifications(1)[0]
        self.notification_page.wait_for_count(1)

        self.devices_page.switch_to_page()

        # idk why those sleeps are needed
        time.sleep(1)

        self.notification_page.click_notification_peek()
        self.notification_page.click_notification(notification_name)
        time.sleep(1)

        self.driver.back()

        time.sleep(1)

        assert self.driver.current_url == self.devices_page.url

    def test_notification_timezone(self):
        self._create_notifications(1)
        self.notification_page.wait_for_count(1)
        self.notification_page.switch_to_page()
        wait_until(func=self.notification_page.get_rows_from_notification_table, total_timeout=60 * 5)
        rows = self.notification_page.get_rows_from_notification_table()
        timestamps = self.notification_page.get_timestamps_from_rows(rows)
        times = [self.notification_page.convert_timestamp_to_datetime(timestamp) for timestamp in timestamps]
        now = datetime.datetime.now()
        seconds_diff = [(now - single_time).total_seconds() for single_time in times]
        assert any(seconds < 60 * 5 for seconds in seconds_diff)

    def test_new_enforcement_no_email_server(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False)
        self.settings_page.click_save_global_settings()

        self.enforcements_page.create_basic_enforcement(ENFORCEMENT_NAME, COMMON_ENFORCEMENT_QUERY)
        self.enforcements_page.add_send_email()
        self.enforcements_page.find_missing_email_server_notification()

    @flaky(max_runs=3)
    def test_syslog_operation_multiple_actions(self):
        syslog_server = SyslogService()
        syslog_server.take_process_ownership()

        with syslog_server.contextmanager():
            # set up syslog in settings
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_syslog_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True)
            self.settings_page.fill_syslog_host(f'{syslog_server.name}.{AXONIUS_DNS_SUFFIX}')
            self.settings_page.fill_syslog_port(syslog_server.tcp_port)
            self.settings_page.select_syslog_ssl('Unencrypted')
            self.settings_page.click_save_button()

            # switch to enforcements page
            self.enforcements_page.create_basic_enforcement(ENFORCEMENT_NAME, COMMON_ENFORCEMENT_QUERY)
            self.enforcements_page.add_push_system_notification()

            self.enforcements_page.add_notify_syslog(action_cond=self.enforcements_page.POST_ACTIONS_TEXT)
            self.enforcements_page.click_save_button()

            self.base_page.run_discovery()
            syslog_expected = f'Alert - "{ENFORCEMENT_NAME}"' + \
                              f' for the following query has been triggered: {COMMON_ENFORCEMENT_QUERY}'
            _verify_in_syslog_data(syslog_server, syslog_expected)

            # Verifying the multiple actions in enforcement worked
            self.notification_page.wait_for_count(1)

            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_syslog_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True)
            self.settings_page.fill_syslog_host(syslog_server.name)
            self.settings_page.fill_syslog_port(syslog_server.tls_port)
            self.settings_page.select_syslog_ssl('Unverified')
            self.settings_page.click_save_button()

            # make another enforcement
            new_enforcement_name = f'{ENFORCEMENT_NAME} SSL'
            self.enforcements_page.create_basic_enforcement(new_enforcement_name, COMMON_ENFORCEMENT_QUERY)
            self.enforcements_page.add_push_system_notification(f'{ENFORCEMENT_NAME} push')

            self.enforcements_page.add_notify_syslog(f'{ENFORCEMENT_NAME} syslog',
                                                     action_cond=self.enforcements_page.POST_ACTIONS_TEXT)
            self.enforcements_page.click_save_button()

            self.base_page.run_discovery()
            syslog_expected = f'Alert - "{new_enforcement_name}"' + \
                              f' for the following query has been triggered: {COMMON_ENFORCEMENT_QUERY}'
            _verify_in_syslog_data(syslog_server, syslog_expected)

    @flaky(max_runs=3)
    def test_tag_entities(self):
        self.adapters_page.clean_adapter_servers(JSON_ADAPTER_NAME)

        # This is here to see if this is really the issue: All tests should start with no devices
        assert self.axonius_system.get_devices_db().count_documents({}) == 0

        self.devices_page.switch_to_page()
        self.devices_page.run_filter_and_save(ENFORCEMENT_CHANGE_NAME,
                                              AD_LAST_OR_ADDED_QUERY.format(added_filter=self.devices_page.
                                                                            JSON_ADAPTER_FILTER))
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.fill_enforcement_name(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.add_tag_entities(ENFORCEMENT_CHANGE_NAME, TAG_ALL_COMMENT,
                                                self.enforcements_page.POST_ACTIONS_TEXT)
        self.enforcements_page.click_save_button()
        self.base_page.run_discovery()

        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(AD_LAST_OR_ADDED_QUERY.format(added_filter=self.devices_page.
                                                                    JSON_ADAPTER_FILTER))
        self.devices_page.enter_search()
        self.enforcements_page.wait_for_table_to_load()
        assert self.devices_page.get_first_row_tags() == TAG_ALL_COMMENT

        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.edit_enforcement(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.change_tag_entities(ENFORCEMENT_CHANGE_NAME, TAG_NEW_COMMENT)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_conditions()
        self.enforcements_page.check_condition_added()
        self.enforcements_page.check_new_entities()
        self.enforcements_page.save_trigger()
        self.enforcements_page.click_save_button()

        # the EC moves us to a page in a weird way, let's wait for it to finish
        time.sleep(1)

        # restore JSON client
        self.adapters_page.add_server(json_file_creds, JSON_ADAPTER_NAME)
        time.sleep(1)

        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(self.devices_page.JSON_ADAPTER_FILTER)
        self.devices_page.enter_search()
        self.enforcements_page.wait_for_table_to_load()
        assert self.devices_page.get_first_row_tags() == TAG_NEW_COMMENT

    def test_enforcement_customized_email(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()

        with smtp_service.contextmanager():
            self.settings_page.add_email_server(smtp_service.fqdn, smtp_service.port)

            self.devices_page.switch_to_page()
            self.base_page.run_discovery()
            test_query = AD_LAST_OR_ADDED_QUERY.format(added_filter=self.devices_page.JSON_ADAPTER_FILTER)
            self.devices_page.run_filter_and_save(ENFORCEMENT_CHANGE_NAME, test_query,
                                                  optional_sort=self.devices_page.FIELD_HOSTNAME_TITLE)
            self.enforcements_page.switch_to_page()
            self.enforcements_page.click_new_enforcement()
            self.enforcements_page.wait_for_spinner_to_end()
            self.enforcements_page.fill_enforcement_name(ENFORCEMENT_NAME)
            self.enforcements_page.select_trigger()
            self.enforcements_page.check_scheduling()
            self.enforcements_page.select_saved_view(ENFORCEMENT_CHANGE_NAME)
            self.enforcements_page.save_trigger()
            self.enforcements_page.add_send_email()
            recipient = generate_random_valid_email()
            customized_body = 'What a beautiful and insightful alert sent by email directly from the enforcement ' \
                              'center of the best Cybersecurity Asset Management system. Axonius is the most ' \
                              'confident place to secure your precious network assets.'
            self.enforcements_page.fill_send_email_config('Special Customized Email', recipient,
                                                          customized_body, True)
            self.enforcements_page.click_save_button()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.execute_saved_query(ENFORCEMENT_CHANGE_NAME)
            devices_count = self.devices_page.count_entities()
            smtp_service.verify_email_send(recipient)
            mail_content = smtp_service.get_email_first_csv_content(recipient)

            assert len(mail_content.splitlines()) == devices_count + 1

            # Testing that it is truly sorted
            hostnames = [x[self.devices_page.FIELD_HOSTNAME_TITLE] for x in make_dict_from_csv(str(mail_content))]
            assert hostnames == sorted(hostnames, reverse=True)

        self.settings_page.remove_email_server()

    def test_enforcement_email_validation(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()

        with smtp_service.contextmanager():
            self.settings_page.add_email_server(smtp_service.fqdn, smtp_service.port)

            self.devices_page.switch_to_page()
            self.devices_page.run_filter_and_save(ENFORCEMENT_CHANGE_NAME, AD_LAST_OR_ADDED_QUERY.format(
                added_filter=self.devices_page.JSON_ADAPTER_FILTER))
            self.enforcements_page.switch_to_page()
            self.enforcements_page.click_new_enforcement()
            self.enforcements_page.wait_for_spinner_to_end()
            self.enforcements_page.fill_enforcement_name(ENFORCEMENT_NAME)
            self.enforcements_page.select_trigger()
            self.enforcements_page.check_scheduling()
            self.enforcements_page.select_saved_view(ENFORCEMENT_CHANGE_NAME)
            self.enforcements_page.save_trigger()
            self.enforcements_page.add_send_email()
            with pytest.raises(NoSuchElementException):
                self.enforcements_page.fill_send_email_config('Special Customized Email')
                # Bad - means the form is valid although is is missing required fields

            # Good - means the button is disabled, as wanted
            assert self.enforcements_page.find_disabled_save_action()
        self.settings_page.remove_email_server()

    def test_tag_entities_dropdown(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.base_page.run_discovery()
        # create new task to add custom tag to all windows based devices
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.fill_enforcement_name(ENFORCEMENT_TEST_NAME_1)
        self.enforcements_page.select_trigger()
        self.enforcements_page.select_saved_view(Enforcements.enforcement_query_1)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification(name='first push')
        self.enforcements_page.add_tag_entities(ENFORCEMENT_TEST_NAME_1, CUSTOM_TAG,
                                                self.enforcements_page.POST_ACTIONS_TEXT)
        self.enforcements_page.click_run_button()
        self.check_tag_added(Enforcements.enforcement_query_1, CUSTOM_TAG)
        self.devices_page.refresh()
        # create new task to remove custom tag to all windows based devices
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.fill_enforcement_name(ENFORCEMENT_TEST_NAME_2)
        self.enforcements_page.select_trigger()
        self.enforcements_page.select_saved_view(Enforcements.enforcement_query_1)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification(name='second push')
        self.enforcements_page.remove_tag_entities(ENFORCEMENT_TEST_NAME_2, CUSTOM_TAG,
                                                   self.enforcements_page.POST_ACTIONS_TEXT)
        self.enforcements_page.click_run_button()
        # go to device page and check if the tag removed
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.fill_filter(CUSTOM_TAG)
        self.devices_page.enter_search()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == 0
        # check if tag value didnt lost in the task
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.edit_enforcement(ENFORCEMENT_TEST_NAME_2)
        self.enforcements_page.find_element_by_text(self.enforcements_page.POST_ACTIONS_TEXT).click()
        self.driver.find_element_by_xpath(
            self.enforcements_page.ADDED_ACTION_XPATH.format(action_name=ENFORCEMENT_TEST_NAME_2)).click()
        self.enforcements_page.wait_for_action_config()
        current_selected_tag = self.enforcements_page.get_tag_dropdown_selected_value()
        assert current_selected_tag == CUSTOM_TAG
        self.enforcements_page.click_save_button()
        # create new task to add new custom tag to all windows based devices
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.fill_enforcement_name(ENFORCEMENT_TEST_NAME_3)
        self.enforcements_page.select_trigger()
        self.enforcements_page.select_saved_view(Enforcements.enforcement_query_1)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification(name='third push')
        self.enforcements_page.select_tag_entities(ENFORCEMENT_TEST_NAME_3, TAG_ALL_COMMENT,
                                                   self.enforcements_page.POST_ACTIONS_TEXT)
        self.enforcements_page.click_run_button()
        self.check_tag_added(Enforcements.enforcement_query_1, TAG_ALL_COMMENT)

    def check_tag_added(self, query, tag):
        # go to device page and check if the tag added
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.execute_saved_query(query)
        self.devices_page.wait_for_table_to_load()
        count = self.enforcements_page.count_entities()
        self.devices_page.fill_filter(tag)
        self.devices_page.enter_search()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == count

    def test_enforcement_s3_csv(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
            with stress.contextmanager(take_ownership=True), \
                    stress_scanner.contextmanager(take_ownership=True):
                device_dict = {'device_count': 10, 'name': 'blah'}
                stress.add_client(device_dict)
                stress_scanner.add_client(device_dict)
                self.devices_page.switch_to_page()
                self.base_page.run_discovery()
                self.devices_page.run_filter_and_save(ENFORCEMENT_CHANGE_NAME, self.DATA_QUERY,
                                                      optional_sort=self.devices_page.FIELD_HOSTNAME_TITLE)
                self.enforcements_page.switch_to_page()
                self.enforcements_page.click_new_enforcement()
                self.enforcements_page.wait_for_spinner_to_end()
                self.enforcements_page.fill_enforcement_name(ENFORCEMENT_NAME)
                self.enforcements_page.select_trigger()
                self.enforcements_page.check_scheduling()
                self.enforcements_page.select_saved_view(ENFORCEMENT_CHANGE_NAME)
                self.enforcements_page.save_trigger()
                self.enforcements_page.add_send_csv_to_s3()

                self.enforcements_page.fill_send_csv_to_s3_config('Send s3 csv',
                                                                  AXONIUS_CI_TESTS_BUCKET,
                                                                  EC2_ECS_EKS_READONLY_ACCESS_KEY_ID,
                                                                  EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY)
                self.enforcements_page.click_save_button()
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                self.devices_page.execute_saved_query(ENFORCEMENT_CHANGE_NAME)
                devices_count = self.devices_page.count_entities()

                file_name_pattern = 'S3 csv file name: (.*)\\.csv'

                wait_until(
                    lambda: LogTester(REPORTS_LOG_PATH).is_pattern_in_log(
                        file_name_pattern, 10))

                log_rows = LogTester(REPORTS_LOG_PATH).get_pattern_lines_from_log(file_name_pattern, 10)
                file_name = log_rows[len(log_rows) - 1].split(':', 1)[1].strip()

                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=EC2_ECS_EKS_READONLY_ACCESS_KEY_ID,
                    aws_secret_access_key=EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY
                )

                response = s3_client.get_object(Bucket=AXONIUS_CI_TESTS_BUCKET, Key=file_name)
                mail_content = response['Body'].read().decode('utf-8')
                assert len(mail_content.splitlines()) == devices_count + 1

                # Testing that it is truly sorted
                hostnames = [x[self.devices_page.FIELD_HOSTNAME_TITLE] for x in make_dict_from_csv(str(mail_content))]
                assert hostnames == sorted(hostnames, reverse=True)
        finally:
            if s3_client and file_name:
                s3_client.delete_object(Bucket=AXONIUS_CI_TESTS_BUCKET, Key=file_name)

    def assert_completed_tasks(self, expected_completed_count):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.click_tasks_button()
        self.enforcements_page.wait_for_table_to_load()

        count = len(self.enforcements_page.find_elements_by_xpath(self.enforcements_page.COMPLETED_CELL_XPATH))
        return count == expected_completed_count

    def test_custom_data_action(self):

        enforcement_db_like = {
            'enforcement_name': 'Custom Data - db identifier name',
            'action_name': 'custom data action 1',
            'field_name': 'hostname',
            'field_value': 'axonius.hostname.db'
        }

        enforcement_label_like = {
            'enforcement_name': 'Custom Data - field name similar to the generic field label',
            'action_name': 'custom data action 2',
            'field_name': 'Host Name',
            'field_value': 'axonius.hostname.label'
        }

        enforcement_unique_field = {
            'enforcement_name': 'Custom Data - unique field',
            'action_name': 'custom data action 3',
            'field_name': 'axonius',
            'field_value': 'axonius.hostname.unique'
        }

        # field name is similar to how generic 'Host Name' saved on db
        self.enforcements_page.create_new_enforcement_with_custom_data(**enforcement_db_like)

        # field name is similar to generic 'Host Name' label
        self.enforcements_page.create_new_enforcement_with_custom_data(**enforcement_label_like)

        # unique field
        self.enforcements_page.create_new_enforcement_with_custom_data(**enforcement_unique_field)

        self.adapters_page.switch_to_page()
        self.base_page.run_discovery()

        # go to devices page, run discovery and run all 3 enforcements on a device
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row_checkbox()

        self.devices_page.run_enforcement_on_selected_device(
            enforcement_name=enforcement_label_like['enforcement_name'])
        self.devices_page.run_enforcement_on_selected_device(
            enforcement_name=enforcement_unique_field['enforcement_name'])
        self.devices_page.run_enforcement_on_selected_device(enforcement_name=enforcement_db_like['enforcement_name'])

        # check in enforcements tasks that all running enforcements were completed
        wait_until(lambda: self.assert_completed_tasks(expected_completed_count=3))

        # go back to devices page and inspect the first device in table
        self.devices_page.switch_to_page()
        self.devices_page.refresh()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.click_row()

        self.devices_page.click_custom_data_tab()

        self.base_page.wait_for_element_present_by_xpath(
            self.enforcements_page.CUSTOM_DATA_XPATH.format(
                db_identifier='custom_hostname',
                label=enforcement_db_like['field_name'],
                value=enforcement_db_like['field_value'])
        )

        self.base_page.wait_for_element_present_by_xpath(
            self.enforcements_page.CUSTOM_DATA_XPATH.format(
                db_identifier='hostname',
                label=enforcement_label_like['field_name'],
                value=enforcement_label_like['field_value'])
        )

        self.base_page.wait_for_element_present_by_xpath(
            self.enforcements_page.CUSTOM_DATA_XPATH.format(
                db_identifier='custom_axonius',
                label=enforcement_unique_field['field_name'],
                value=enforcement_unique_field['field_value'])
        )
