import datetime
from typing import List

import pytest
from retrying import retry
from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until
from services.adapters.json_file_service import JsonFileService
from services.standalone_services.syslog_server import SyslogService
from ui_tests.tests.ui_test_base import TestBase

ALERT_NAME = 'Special alert name'
COMMON_ALERT_QUERY = 'Enabled AD Devices'

ALERT_CHANGE_NAME = 'test_alert_change'
ALERT_CHANGE_FILTER = 'adapters_data.json_file_adapter.test_alert_change == 5'

AD_LAST_OR_ADDED_QUERY = '({added_filter}) or adapters_data.active_directory_adapter.ad_last_logon> date("NOW-8d")'
ALERT_NUMBER_OF_DEVICES = 21

TAG_ALL_COMMENT = 'tag all'
TAG_NEW_COMMENT = 'tag new'


@retry(stop_max_attempt_number=100, wait_fixed=100)
def _verify_in_syslog_data(syslog_service: SyslogService, text):
    last_log = list(syslog_service.get_syslog_data())[-10:]
    assert any(bytes(text, 'ascii') in l for l in last_log)


def create_alert_name(number, alert_name=ALERT_NAME):
    return f'{alert_name} {number}'


class TestAlert(TestBase):

    def create_alert_change_query(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.run_filter_and_save(ALERT_CHANGE_NAME, ALERT_CHANGE_FILTER)

    def create_notifications(self, count=1, name=ALERT_NAME) -> List[str]:
        result = []
        for i in range(count):
            alert_name = create_alert_name(i)
            self.alert_page.create_outputting_notification_alert(alert_name, COMMON_ALERT_QUERY)
            result.append(alert_name)
        self.base_page.run_discovery()
        return result

    def test_new_alert_no_email_server(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False)
        self.settings_page.click_save_global_settings()

        self.alert_page.create_basic_alert(ALERT_NAME, COMMON_ALERT_QUERY)
        self.alert_page.click_send_an_email()
        self.alert_page.find_missing_email_server_notification()

    def test_remove_alert(self):
        self.alert_page.create_outputting_notification_alert(ALERT_NAME, COMMON_ALERT_QUERY)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_NAME)
        old_length = len(self.notification_page.get_peek_notifications())

        self.alert_page.switch_to_page()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.wait_for_table_to_load()
        self.alert_page.select_all_alerts()
        self.alert_page.remove_selected_alerts()

        self.base_page.run_discovery()
        new_length = len(self.notification_page.get_peek_notifications())

        assert old_length == new_length

    def test_invalid_input(self):
        self.alert_page.create_basic_alert(ALERT_NAME, COMMON_ALERT_QUERY)
        self.alert_page.check_above()
        self.alert_page.fill_above_value(-5)
        value = self.alert_page.get_above_value()
        assert value == '5'

    def test_alert_changing_triggers(self):
        self.create_alert_change_query()
        self.alert_page.switch_to_page()
        self.alert_page.wait_for_table_to_load()
        self.alert_page.click_new_alert()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.fill_alert_name(ALERT_CHANGE_NAME)
        self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
        self.alert_page.check_every_discovery()
        self.alert_page.check_push_system_notification()
        self.alert_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

        self.alert_page.wait_for_table_to_load()
        self.alert_page.edit_alert(ALERT_CHANGE_NAME)
        self.alert_page.wait_for_spinner_to_end()
        # uncheck Not Changed
        self.alert_page.check_every_discovery()
        self.alert_page.check_below()
        self.alert_page.fill_below_value(1)
        self.alert_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is still 1
        self.notification_page.verify_amount_of_notifications(1)

        json_service = JsonFileService()
        json_service.take_process_ownership()
        json_service.stop(should_delete=False)

        try:
            # Making the query return 0 results
            db = self.axonius_system.get_devices_db()
            result = db.update_one({'adapters.data.test_alert_change': 5},
                                   {'$set': {'adapters.$.data.test_alert_change': 4}})
            assert result.modified_count == 1
            self.base_page.run_discovery()
            # make sure it is now 2
            self.notification_page.verify_amount_of_notifications(2)

        finally:
            json_service.start_and_wait()

    def test_new(self):
        json_service = JsonFileService()
        json_service.take_process_ownership()
        try:
            json_service.stop(should_delete=False)
            self.create_alert_change_query()
            self.alert_page.switch_to_page()
            self.alert_page.wait_for_table_to_load()
            self.alert_page.click_new_alert()
            self.alert_page.wait_for_spinner_to_end()
            self.alert_page.fill_alert_name(ALERT_CHANGE_NAME)
            self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
            self.alert_page.check_new()
            self.alert_page.check_push_system_notification()
            self.alert_page.click_save_button()

            self.base_page.run_discovery()
            self.notification_page.verify_amount_of_notifications(0)
        finally:
            json_service.start_and_wait()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

    def test_tag_entities(self):
        json_service = JsonFileService()
        json_service.take_process_ownership()
        try:
            json_service.stop(should_delete=False)
            self.devices_page.switch_to_page()
            self.devices_page.run_filter_and_save(ALERT_CHANGE_NAME,
                                                  AD_LAST_OR_ADDED_QUERY.format(added_filter=self.devices_page.
                                                                                JSON_ADAPTER_FILTER))
            self.alert_page.switch_to_page()
            self.alert_page.wait_for_table_to_load()
            self.alert_page.click_new_alert()
            self.alert_page.wait_for_spinner_to_end()
            self.alert_page.fill_alert_name(ALERT_CHANGE_NAME)
            self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
            self.alert_page.check_every_discovery()
            self.alert_page.check_push_system_notification()
            self.alert_page.click_tag_all_entities()
            self.alert_page.fill_tag_all_text(TAG_ALL_COMMENT)
            self.alert_page.click_save_button()
            self.base_page.run_discovery()

            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(AD_LAST_OR_ADDED_QUERY.format(added_filter=self.devices_page.
                                                                        JSON_ADAPTER_FILTER))
            self.devices_page.enter_search()
            assert self.devices_page.get_first_row_tags() == TAG_ALL_COMMENT

            self.alert_page.switch_to_page()
            self.alert_page.edit_alert(ALERT_CHANGE_NAME)
            self.alert_page.wait_for_spinner_to_end()
            self.alert_page.check_every_discovery()
            self.alert_page.check_new()
            self.alert_page.click_tag_all_entities()
            self.alert_page.click_tag_new_entities()
            self.alert_page.fill_tag_new_text(TAG_NEW_COMMENT)
            self.alert_page.click_save_button()
        finally:
            json_service.start_and_wait()

        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(self.devices_page.JSON_ADAPTER_FILTER)
        self.devices_page.enter_search()
        assert self.devices_page.get_first_row_tags() == TAG_NEW_COMMENT

    def test_save_query_deletion(self):
        self.create_alert_change_query()
        self.alert_page.switch_to_page()
        self.alert_page.wait_for_table_to_load()
        self.alert_page.click_new_alert()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.fill_alert_name(ALERT_CHANGE_NAME)
        self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
        self.alert_page.check_every_discovery()
        self.alert_page.check_push_system_notification()
        self.alert_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(ALERT_CHANGE_NAME)
        self.devices_queries_page.remove_selected_queries()

        self.alert_page.switch_to_page()
        self.alert_page.wait_for_table_to_load()
        self.alert_page.edit_alert(ALERT_CHANGE_NAME)
        self.alert_page.wait_for_spinner_to_end()

        self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
        text = self.alert_page.get_saved_query_text()
        formatted = f'{ALERT_CHANGE_NAME} (deleted)'
        assert text == formatted

    def test_delete_saved_query(self):
        self.create_alert_change_query()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(ALERT_CHANGE_NAME)
        self.devices_queries_page.remove_selected_queries()
        self.driver.refresh()
        with pytest.raises(NoSuchElementException):
            self.devices_queries_page.find_query_row_by_name(ALERT_CHANGE_NAME)

    def test_edit_alert(self):
        self.create_alert_change_query()
        self.alert_page.switch_to_page()
        self.alert_page.wait_for_table_to_load()
        self.alert_page.click_new_alert()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.fill_alert_name(ALERT_CHANGE_NAME)
        self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
        self.alert_page.check_previous()
        self.alert_page.check_push_system_notification()
        self.alert_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.alert_page.wait_for_table_to_load()
        self.alert_page.edit_alert(ALERT_CHANGE_NAME)
        self.alert_page.wait_for_spinner_to_end()
        # uncheck Below
        self.alert_page.check_previous()
        self.alert_page.check_every_discovery()
        self.alert_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is now 1
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

    def test_syslog_operation_multiple_actions(self):
        syslog_server = SyslogService()
        syslog_server.take_process_ownership()

        with syslog_server.contextmanager():
            # set up syslog in settings
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_syslog_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True)
            self.settings_page.fill_syslog_host(syslog_server.name)
            self.settings_page.fill_syslog_port(syslog_server.tcp_port)
            self.settings_page.select_syslog_ssl('Unencrypted')
            self.settings_page.click_save_button()

            # switch to alerts page
            self.alert_page.create_basic_alert(ALERT_NAME, COMMON_ALERT_QUERY)

            # check all trigger causes so it will always jump
            self.alert_page.check_every_discovery()
            self.alert_page.check_new()
            self.alert_page.check_previous()

            self.alert_page.check_push_system_notification()

            # This is here because our syslog doesn't like logs sent using "INFO"
            # this is an issue with our syslog's configuration, and it's not worth the time fixing
            self.alert_page.choose_severity_warning()

            self.alert_page.check_notify_syslog()
            self.alert_page.click_save_button()

            self.base_page.run_discovery()
            syslog_expected = f'Axonius:Alert - "{ALERT_NAME}"' + \
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
            new_alert_name = f'{ALERT_NAME}_SSL'
            self.alert_page.create_basic_alert(new_alert_name, COMMON_ALERT_QUERY)

            # check all trigger causes so it will always jump
            self.alert_page.check_every_discovery()
            self.alert_page.check_new()
            self.alert_page.check_previous()

            self.alert_page.check_push_system_notification()

            # This is here because our syslog doesn't like logs sent using "INFO"
            # this is an issue with our syslog's configuration, and it's not worth the time fixing
            self.alert_page.choose_severity_warning()

            self.alert_page.check_notify_syslog()
            self.alert_page.click_save_button()

            self.base_page.run_discovery()
            syslog_expected = f'Axonius:Alert - "{new_alert_name}"' + \
                              f' for the following query has been triggered: {COMMON_ALERT_QUERY}'
            _verify_in_syslog_data(syslog_server, syslog_expected)

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

        self.devices_page.switch_to_page()
        self.notification_page.click_notification_peek()
        self.notification_page.click_notification(notification_name)
        self.driver.back()
        assert self.driver.current_url == self.devices_page.url

    def test_notification_timezone(self):
        self.create_notifications(1)
        self.notification_page.switch_to_page()
        wait_until(func=self.notification_page.get_rows_from_notification_table, total_timeout=60 * 5)
        rows = self.notification_page.get_rows_from_notification_table()
        timestamps = self.notification_page.get_timestamps_from_rows(rows)
        times = [self.notification_page.convert_timestamp_to_datetime(timestamp) for timestamp in timestamps]
        now = datetime.datetime.now()
        seconds_diff = [(now - single_time).total_seconds() for single_time in times]
        assert any(seconds < 60 * 5 for seconds in seconds_diff)

    def test_above_threshold(self):
        self.alert_page.create_outputting_notification_above('above 1',
                                                             COMMON_ALERT_QUERY,
                                                             above=ALERT_NUMBER_OF_DEVICES + 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.alert_page.create_outputting_notification_above('above 2',
                                                             COMMON_ALERT_QUERY,
                                                             above=ALERT_NUMBER_OF_DEVICES - 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)

    def test_below_threshold(self):
        self.alert_page.create_outputting_notification_below('below 1',
                                                             COMMON_ALERT_QUERY,
                                                             below=ALERT_NUMBER_OF_DEVICES - 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.alert_page.create_outputting_notification_below('below 2',
                                                             COMMON_ALERT_QUERY,
                                                             below=ALERT_NUMBER_OF_DEVICES + 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
