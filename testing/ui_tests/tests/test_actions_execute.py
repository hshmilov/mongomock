import datetime
from typing import List

from retrying import retry
from flaky import flaky

from axonius.utils.wait import wait_until
from services.adapters.json_file_service import JsonFileService
from services.standalone_services.syslog_server import SyslogService
from ui_tests.tests.ui_test_base import TestBase

ENFORCEMENT_NAME = 'Special enforcement name'
COMMON_ALERT_QUERY = 'Enabled AD Devices'
ALERT_CHANGE_NAME = 'test_alert_change'

SAVED_QUERY_JUST_CBR_NAME = 'just_cbr'
SAVED_QUERY_JUST_CBR = 'adapters == \'carbonblack_response_adapter\''
AD_LAST_OR_ADDED_QUERY = '({added_filter}) or adapters_data.active_directory_adapter.ad_last_logon> date("NOW-8d")'

TAG_ALL_COMMENT = 'tag all'
TAG_NEW_COMMENT = 'tag new'


def create_enforcement_name(number, enforcement_name=ENFORCEMENT_NAME):
    return f'{enforcement_name} {number}'


@retry(stop_max_attempt_number=5 * 60, wait_fixed=1000)
def _verify_in_syslog_data(syslog_service: SyslogService, text):
    last_log = list(syslog_service.get_syslog_data())[-100:]
    assert any(bytes(text, 'ascii') in l for l in last_log)


class TestAlertActions(TestBase):
    def create_notifications(self, count=1) -> List[str]:
        result = []
        for i in range(count):
            alert_name = create_enforcement_name(i)
            self.enforcements_page.create_notifying_enforcement(alert_name, COMMON_ALERT_QUERY)
            result.append(alert_name)
        self.base_page.run_discovery()
        return result

    def test_notification_sanity(self):
        self.create_notifications(2)

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
        self.create_notifications(7)
        self.notification_page.wait_for_count(7)

        assert len(self.notification_page.get_peek_notifications()) == 6

    def test_single_notification(self):
        notification_name = self.create_notifications(1)[0]
        self.notification_page.wait_for_count(1)

        self.devices_page.switch_to_page()
        self.notification_page.click_notification_peek()
        self.notification_page.click_notification(notification_name)
        self.driver.back()
        assert self.driver.current_url == self.devices_page.url

    def test_notification_timezone(self):
        self.create_notifications(1)
        self.notification_page.wait_for_count(1)
        self.notification_page.switch_to_page()
        wait_until(func=self.notification_page.get_rows_from_notification_table, total_timeout=60 * 5)
        rows = self.notification_page.get_rows_from_notification_table()
        timestamps = self.notification_page.get_timestamps_from_rows(rows)
        times = [self.notification_page.convert_timestamp_to_datetime(timestamp) for timestamp in timestamps]
        now = datetime.datetime.now()
        seconds_diff = [(now - single_time).total_seconds() for single_time in times]
        assert any(seconds < 60 * 5 for seconds in seconds_diff)

    def test_new_alert_no_email_server(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False)
        self.settings_page.click_save_global_settings()

        self.enforcements_page.create_basic_enforcement(ENFORCEMENT_NAME, COMMON_ALERT_QUERY)
        self.enforcements_page.add_send_email()
        self.enforcements_page.find_missing_email_server_notification()

    def test_syslog_operation_multiple_actions(self):
        syslog_server = SyslogService()
        syslog_server.take_process_ownership()

        with syslog_server.contextmanager():
            # set up syslog in settings
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_syslog_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True)
            self.settings_page.fill_syslog_host(f'{syslog_server.name}.axonius.local')
            self.settings_page.fill_syslog_port(syslog_server.tcp_port)
            self.settings_page.select_syslog_ssl('Unencrypted')
            self.settings_page.click_save_button()

            # switch to alerts page
            self.enforcements_page.create_basic_enforcement(ENFORCEMENT_NAME, COMMON_ALERT_QUERY)
            self.enforcements_page.add_push_system_notification()

            self.enforcements_page.add_notify_syslog(is_main=False)
            self.enforcements_page.click_save_button()

            self.base_page.run_discovery()
            syslog_expected = f'Axonius:Alert - "{ENFORCEMENT_NAME}"' + \
                              f' for the following query has been triggered: {COMMON_ALERT_QUERY}'
            _verify_in_syslog_data(syslog_server, syslog_expected)

            # Verifying the multiple actions in alert worked
            self.notification_page.verify_amount_of_notifications(1)

            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_syslog_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True)
            self.settings_page.fill_syslog_host(syslog_server.name)
            self.settings_page.fill_syslog_port(syslog_server.tls_port)
            self.settings_page.select_syslog_ssl('Unverified')
            self.settings_page.click_save_button()

            # make another alert
            new_alert_name = f'{ENFORCEMENT_NAME} SSL'
            self.enforcements_page.create_basic_enforcement(new_alert_name, COMMON_ALERT_QUERY)
            self.enforcements_page.add_push_system_notification(f'{ENFORCEMENT_NAME} push')

            self.enforcements_page.add_notify_syslog(f'{ENFORCEMENT_NAME} syslog', False)
            self.enforcements_page.click_save_button()

            self.base_page.run_discovery()
            syslog_expected = f'Axonius:Alert - "{new_alert_name}"' + \
                              f' for the following query has been triggered: {COMMON_ALERT_QUERY}'
            _verify_in_syslog_data(syslog_server, syslog_expected)

    @flaky(max_runs=3)
    def test_tag_entities(self):
        json_service = JsonFileService()
        json_service.take_process_ownership()
        try:
            json_service.stop(should_delete=False)

            # This is here to see if this is really the issue: All tests should start with no devices
            assert self.axonius_system.get_devices_db().count_documents({}) == 0

            self.devices_page.switch_to_page()
            self.devices_page.run_filter_and_save(ALERT_CHANGE_NAME,
                                                  AD_LAST_OR_ADDED_QUERY.format(added_filter=self.devices_page.
                                                                                JSON_ADAPTER_FILTER))
            self.enforcements_page.switch_to_page()
            self.enforcements_page.wait_for_table_to_load()
            self.enforcements_page.click_new_enforcement()
            self.enforcements_page.fill_enforcement_name(ALERT_CHANGE_NAME)
            self.enforcements_page.select_trigger()
            self.enforcements_page.check_scheduling()
            self.enforcements_page.select_saved_view(ALERT_CHANGE_NAME)
            self.enforcements_page.save_trigger()
            self.enforcements_page.add_push_system_notification()
            self.enforcements_page.add_tag_entities(ALERT_CHANGE_NAME, TAG_ALL_COMMENT, False)
            self.enforcements_page.click_save_button()
            self.base_page.run_discovery()

            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(AD_LAST_OR_ADDED_QUERY.format(added_filter=self.devices_page.
                                                                        JSON_ADAPTER_FILTER))
            self.devices_page.enter_search()
            self.enforcements_page.wait_for_table_to_load()
            assert self.devices_page.get_first_row_tags() == TAG_ALL_COMMENT

            self.enforcements_page.switch_to_page()
            self.enforcements_page.edit_enforcement(ALERT_CHANGE_NAME)
            self.enforcements_page.change_tag_entities(ALERT_CHANGE_NAME, TAG_NEW_COMMENT)
            self.enforcements_page.select_trigger()
            self.enforcements_page.check_conditions()
            self.enforcements_page.check_new()
            self.enforcements_page.check_new_entities()
            self.enforcements_page.save_trigger()
            self.enforcements_page.click_save_button()
        finally:
            json_service.start_and_wait()

        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(self.devices_page.JSON_ADAPTER_FILTER)
        self.devices_page.enter_search()
        self.enforcements_page.wait_for_table_to_load()
        assert self.devices_page.get_first_row_tags() == TAG_NEW_COMMENT
