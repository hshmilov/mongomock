import datetime
import time
from typing import List
import pytest
from selenium.common.exceptions import NoSuchElementException

from flaky import flaky
from retrying import retry

from axonius.consts.system_consts import AXONIUS_DNS_SUFFIX
from axonius.utils.wait import wait_until
from axonius.utils.parsing import make_dict_from_csv
from services.standalone_services.smtp_server import generate_random_valid_email
from services.standalone_services.maildiranasaurus_server import MailDiranasaurusService as SMTPService
from services.standalone_services.syslog_server import SyslogService
from ui_tests.tests.ui_test_base import TestBase
from test_credentials.json_file_credentials import client_details as json_file_creds

ENFORCEMENT_NAME = 'Special enforcement name'
COMMON_ENFORCEMENT_QUERY = 'Enabled AD Devices'
ENFORCEMENT_CHANGE_NAME = 'test_enforcement_change'

SAVED_QUERY_JUST_CBR_NAME = 'just_cbr'
SAVED_QUERY_JUST_CBR = 'adapters == \'carbonblack_response_adapter\''
AD_LAST_OR_ADDED_QUERY = '({added_filter}) or adapters_data.active_directory_adapter.ad_last_logon> date("NOW-8d")'

TAG_ALL_COMMENT = 'tag all'
TAG_NEW_COMMENT = 'tag new'

JSON_ADAPTER_NAME = 'JSON File'


def create_enforcement_name(number, enforcement_name=ENFORCEMENT_NAME):
    return f'{enforcement_name} {number}'


@retry(stop_max_attempt_number=5 * 60, wait_fixed=1000)
def _verify_in_syslog_data(syslog_service: SyslogService, text):
    last_log = list(syslog_service.get_syslog_data())[-100:]
    assert any(bytes(text, 'ascii') in l for l in last_log)


class TestEnforcementActions(TestBase):

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
