import time

import pytest
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.gui_consts import (DASHBOARD_SPACE_DEFAULT,
                                       DASHBOARD_SPACE_PERSONAL)
from axonius.utils.wait import wait_until
from test_credentials.test_gui_credentials import AXONIUS_USER
from ui_tests.tests.ui_consts import (READ_WRITE_USERNAME, READ_ONLY_USERNAME, NEW_PASSWORD,
                                      FIRST_NAME, LAST_NAME, HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME,
                                      IPS_192_168_QUERY, IPS_192_168_QUERY_NAME, OS_TYPE_OPTION_NAME,
                                      WINDOWS_QUERY_NAME, LINUX_QUERY_NAME)
from ui_tests.tests.ui_test_base import TestBase

# pylint: disable=no-member


class TestDashboardCharts(TestBase):

    COVERAGE_SPACE_NAME = 'Coverage Dashboard'
    VULNERABILITY_SPACE_NAME = 'Vulnerability Dashboard'
    CUSTOM_SPACE_PANEL_NAME = 'Segment OS'
    PERSONAL_SPACE_PANEL_NAME = 'Private Segment OS'
    UNCOVERED_QUERY = 'not (((specific_data.data.adapter_properties == "Agent") or ' \
                      '(specific_data.data.adapter_properties == "Manager")))'
    COVERED_QUERY = '((specific_data.data.adapter_properties == "Agent") ' \
                    'or (specific_data.data.adapter_properties == "Manager"))'
    TEST_INTERSECTION_TITLE = 'test intersection'
    INTERSECTION_QUERY = f'({IPS_192_168_QUERY}) and ({HOSTNAME_DC_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY = f'({IPS_192_168_QUERY}) and not ({HOSTNAME_DC_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY = f'not (({IPS_192_168_QUERY}) or ({HOSTNAME_DC_QUERY}))'
    TEST_SUMMARY_TITLE_DEVICES = 'test summary devices'
    SUMMARY_CARD_QUERY_DEVICES = 'specific_data.data.hostname == exists(true)'
    SUMMARY_CARD_QUERY_USERS = 'specific_data.data.logon_count == exists(true) and specific_data.data.logon_count > 0'
    TEST_SUMMARY_TITLE_USERS = 'test summary users'
    TEST_SEGMENTATION_HISTOGRAM_TITLE = 'test segmentation histogram'
    NO_OS_QUERY = 'not (specific_data.data.os.type == exists(true))'
    TEST_SEGMENTATION_PIE_TITLE = 'test segmentation pie'
    SEGMENTATION_PIE_CARD_QUERY = 'specific_data.data.hostname == '
    OS_WINDOWS_QUERY = 'specific_data.data.os.type == "Windows"'
    OSX_OPERATING_SYSTEM_FILTER = 'specific_data.data.os.type == "OS X"'
    OSX_OPERATING_SYSTEM_NAME = 'OS X Operating System'
    TEST_EMPTY_TITLE = 'test empty'
    TEST_MOVE_PANEL = 'test move panel'
    TEST_EDIT_CHART_TITLE = 'test edit'

    def test_dashboard_spaces(self):
        # Default space and Personal space existing
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_active_space_header_title() == DASHBOARD_SPACE_DEFAULT
        assert self.dashboard_page.find_space_header_title(2) == DASHBOARD_SPACE_PERSONAL

        # Add new space and name it
        self.dashboard_page.add_new_space(self.COVERAGE_SPACE_NAME)
        wait_until(lambda: self.dashboard_page.find_space_header_title(3) == self.COVERAGE_SPACE_NAME)

        # Rename an existing space
        self.dashboard_page.rename_space(self.VULNERABILITY_SPACE_NAME, 3)
        wait_until(lambda: self.dashboard_page.find_space_header_title(3) == self.VULNERABILITY_SPACE_NAME)
        assert self.dashboard_page.is_missing_space(self.COVERAGE_SPACE_NAME)
        self.dashboard_page.add_new_space(self.COVERAGE_SPACE_NAME)

        # Add a panel to a custom space
        self.dashboard_page.find_space_header(3).click()
        self.dashboard_page.add_segmentation_card('Devices', OS_TYPE_OPTION_NAME, self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.wait_for_spinner_to_end()
        segment_card = self.dashboard_page.get_card(self.CUSTOM_SPACE_PANEL_NAME)
        assert segment_card and self.dashboard_page.get_histogram_chart_from_card(segment_card)
        self.dashboard_page.find_space_header(1).click()
        assert self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.find_space_header(2).click()
        assert self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)

        # Add a panel to the Personal space and check hidden from other user
        self.dashboard_page.add_segmentation_card('Devices', OS_TYPE_OPTION_NAME, self.PERSONAL_SPACE_PANEL_NAME)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(READ_WRITE_USERNAME, NEW_PASSWORD,
                                           FIRST_NAME, LAST_NAME,
                                           role_name=self.settings_page.ADMIN_ROLE)
        self.settings_page.add_user_with_duplicated_role(READ_ONLY_USERNAME, NEW_PASSWORD,
                                                         FIRST_NAME, LAST_NAME,
                                                         role_to_duplicate=self.settings_page.VIEWER_ROLE)
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_WRITE_USERNAME, password=NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.find_space_header(2).click()
        assert self.dashboard_page.is_missing_panel(self.PERSONAL_SPACE_PANEL_NAME)
        assert not self.dashboard_page.is_missing_space(self.VULNERABILITY_SPACE_NAME)
        self.dashboard_page.find_space_header(3).click()
        assert not self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.remove_card(self.CUSTOM_SPACE_PANEL_NAME)
        assert not self.dashboard_page.is_missing_space(self.COVERAGE_SPACE_NAME)
        self.dashboard_page.remove_space(3)
        self.dashboard_page.rename_space(self.VULNERABILITY_SPACE_NAME, 3)

        # Remove a space
        assert self.dashboard_page.is_missing_space(self.COVERAGE_SPACE_NAME)
        self.dashboard_page.remove_space(3)
        assert self.dashboard_page.is_missing_space(self.VULNERABILITY_SPACE_NAME)

        # Login with Read Only user and see it cannot add a space
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_ONLY_USERNAME, password=NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.is_missing_space(DASHBOARD_SPACE_PERSONAL)
        assert self.dashboard_page.is_missing_add_space()
        self._test_read_only_user_with_dashboard_read_write()

    def test_dashboard_coverage_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()

        # Allow the caches to be rebuilt
        time.sleep(5)

        # This triggers a dashboard reload
        self.settings_page.switch_to_page()
        self.dashboard_page.switch_to_page()

        self.dashboard_page.click_uncovered_pie_slice()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.UNCOVERED_QUERY
        self.devices_page.click_query_wizard()
        # make sure there is no error in the wizard
        assert self.devices_page.is_query_error()
        self.devices_page.click_search()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.click_covered_pie_slice()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.COVERED_QUERY
        self.devices_page.click_query_wizard()
        # make sure there is no error in the wizard
        assert self.devices_page.is_query_error()
        self.devices_page.click_search()

    def test_dashboard_intersection_chart(self):
        self.devices_page.create_saved_query(IPS_192_168_QUERY, IPS_192_168_QUERY_NAME)
        self.devices_page.create_saved_query(HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME)
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_intersection_card('Devices',
                                                  IPS_192_168_QUERY_NAME,
                                                  HOSTNAME_DC_QUERY_NAME,
                                                  self.TEST_INTERSECTION_TITLE)
        self.dashboard_page.wait_for_spinner_to_end()
        # verify card config reset
        self.dashboard_page.verify_card_config_reset_intersection_chart(self.TEST_INTERSECTION_TITLE)
        self.dashboard_page.click_intersection_pie_slice(self.TEST_INTERSECTION_TITLE)
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.INTERSECTION_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.click_symmetric_difference_first_query_pie_slice(self.TEST_INTERSECTION_TITLE)
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.click_symmetric_difference_base_query_pie_slice(self.TEST_INTERSECTION_TITLE)
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_card(self.TEST_INTERSECTION_TITLE)

    def test_dashboard_summary_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count', self.TEST_SUMMARY_TITLE_DEVICES)
        self.dashboard_page.wait_for_spinner_to_end()
        # verify card reset config
        self.dashboard_page.verify_card_config_reset_summary_chart(self.TEST_SUMMARY_TITLE_DEVICES)
        summary_chart = self.dashboard_page.get_summary_card_text(self.TEST_SUMMARY_TITLE_DEVICES)
        result_count = int(summary_chart.text)
        summary_chart.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == result_count
        assert self.devices_page.find_search_value() == self.SUMMARY_CARD_QUERY_DEVICES
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_card(self.TEST_SUMMARY_TITLE_DEVICES)
        self.dashboard_page.add_summary_card('Users', 'Logon Count', 'Count', self.TEST_SUMMARY_TITLE_USERS)
        # verify card reset config
        self.dashboard_page.verify_card_config_reset_summary_chart(self.TEST_SUMMARY_TITLE_USERS)
        summary_chart = self.dashboard_page.get_summary_card_text(self.TEST_SUMMARY_TITLE_USERS)
        result_count = int(summary_chart.text)
        summary_chart.click()
        self.users_page.wait_for_table_to_load()
        assert self.users_page.count_entities() == result_count
        assert self.users_page.find_search_value() == self.SUMMARY_CARD_QUERY_USERS
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_card(self.TEST_SUMMARY_TITLE_USERS)

    def test_new_chart_stress(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        for i in range(10):
            self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count',
                                                 f'{self.TEST_SUMMARY_TITLE_DEVICES}{i}')
            self.dashboard_page.wait_for_spinner_to_end()
            self.dashboard_page.get_card(f'{self.TEST_SUMMARY_TITLE_DEVICES}{i}')
        last_card = self.dashboard_page.get_all_cards()[-1]
        assert self.dashboard_page.get_title_from_card(last_card) == 'New Chart'
        for j in range(10):
            self.dashboard_page.remove_card(f'{self.TEST_SUMMARY_TITLE_DEVICES}{j}')
            self.dashboard_page.wait_for_spinner_to_end()

    def test_dashboard_segmentation_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card(
            'Devices', OS_TYPE_OPTION_NAME, self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        # verify config reset
        self.dashboard_page.verify_card_config_reset_segmentation_chart(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        shc_card = self.dashboard_page.get_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        shc_chart = self.dashboard_page.get_histogram_chart_from_card(shc_card)
        line = self.dashboard_page.get_histogram_line_from_histogram(shc_chart, 1)
        first_result_count = int(line.text)
        line.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == first_result_count
        if first_result_count == 1:
            assert self.devices_page.find_search_value() == self.NO_OS_QUERY
        else:
            assert self.devices_page.find_search_value() == self.OS_WINDOWS_QUERY
            self.dashboard_page.switch_to_page()
            shc_card = self.dashboard_page.get_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
            shc_chart = self.dashboard_page.get_histogram_chart_from_card(shc_card)
            line = self.dashboard_page.get_histogram_line_from_histogram(shc_chart, 2)
            second_result_count = int(line.text)
            line.click()
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.count_entities() == second_result_count
            assert self.devices_page.find_search_value() == self.NO_OS_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.add_segmentation_card('Devices', 'Host Name', self.TEST_SEGMENTATION_PIE_TITLE, 'pie')
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.click_segmentation_pie_card(self.TEST_SEGMENTATION_PIE_TITLE)
        self.devices_page.wait_for_table_to_load()
        assert self.SEGMENTATION_PIE_CARD_QUERY in self.devices_page.find_search_value()
        assert self.devices_page.count_entities() == 1
        self.dashboard_page.switch_to_page()

        self._test_dashboard_segmentation_filter()
        self.dashboard_page.remove_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        self.dashboard_page.remove_card(self.TEST_SEGMENTATION_PIE_TITLE)

    def test_dashboard_empty_segmentation_chart(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.OSX_OPERATING_SYSTEM_FILTER, self.OSX_OPERATING_SYSTEM_NAME)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card(module='Devices',
                                                  field=OS_TYPE_OPTION_NAME,
                                                  title=self.TEST_EMPTY_TITLE,
                                                  view_name=self.OSX_OPERATING_SYSTEM_NAME)

        assert self.dashboard_page.find_no_data_label()
        self.dashboard_page.remove_card(self.TEST_EMPTY_TITLE)

    def test_dashboard_empty_intersection_chart(self):
        self.devices_page.create_saved_query(self.OSX_OPERATING_SYSTEM_FILTER, self.OSX_OPERATING_SYSTEM_NAME)
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_intersection_card(module='Devices',
                                                  view_name=self.OSX_OPERATING_SYSTEM_NAME,
                                                  first_query=self.OSX_OPERATING_SYSTEM_NAME,
                                                  second_query=self.OSX_OPERATING_SYSTEM_NAME,
                                                  title=self.TEST_EMPTY_TITLE)

        assert self.dashboard_page.find_no_data_label()
        self.dashboard_page.remove_card(self.TEST_EMPTY_TITLE)

    def test_dashboard_empty_comparison_chart(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.OSX_OPERATING_SYSTEM_FILTER, self.OSX_OPERATING_SYSTEM_NAME)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_comparison_card([{'module': 'Devices', 'query': self.OSX_OPERATING_SYSTEM_NAME},
                                                 {'module': 'Devices', 'query': self.OSX_OPERATING_SYSTEM_NAME}],
                                                title=self.TEST_EMPTY_TITLE,
                                                chart_type='pie')

        assert self.dashboard_page.find_no_data_label()
        self.dashboard_page.remove_card(self.TEST_EMPTY_TITLE)

    def test_dashboard_intersection_chart_config_reset(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_intersection_card('Users', 'AD enabled locked users',
                                                  'AD disabled users', self.TEST_INTERSECTION_TITLE)
        self.dashboard_page.wait_for_spinner_to_end()
        # verify card config reset
        self.dashboard_page.verify_card_config_reset_intersection_chart(self.TEST_INTERSECTION_TITLE)
        self.dashboard_page.remove_card(self.TEST_INTERSECTION_TITLE)

    def test_dashboard_chart_refresh(self):
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_card_spinner_to_end()
        self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count', self.TEST_SUMMARY_TITLE_DEVICES)
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.verify_card_config_reset_summary_chart(self.TEST_SUMMARY_TITLE_DEVICES)
        summary_chart = self.dashboard_page.get_summary_card_text(self.TEST_SUMMARY_TITLE_DEVICES)
        result_count = int(summary_chart.text)
        self.devices_page.switch_to_page()
        self.devices_page.delete_devices()
        self.dashboard_page.switch_to_page()
        summary_chart = self.dashboard_page.get_summary_card_text(self.TEST_SUMMARY_TITLE_DEVICES)
        assert int(summary_chart.text) == result_count
        self.dashboard_page.refresh_card(self.TEST_SUMMARY_TITLE_DEVICES)
        assert self.dashboard_page.find_no_data_label()

    def test_dashboard_chart_move(self):
        card_title = self.TEST_MOVE_PANEL
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_card_spinner_to_end()
        self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count', card_title)
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.open_move_or_copy_card(card_title)
        self.dashboard_page.select_space_for_move_or_copy(DASHBOARD_SPACE_PERSONAL)
        self.dashboard_page.toggle_move_or_copy_checkbox()
        self.dashboard_page.click_button('OK')
        wait_until(lambda: self.dashboard_page.is_missing_panel(card_title))
        self.dashboard_page.find_space_header(2).click()
        last_card = self.dashboard_page.get_last_card_created()
        assert self.dashboard_page.get_title_from_card(last_card) == card_title.title()
        self.dashboard_page.remove_card(card_title)

    def test_dashboard_edit_module(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.create_saved_query(self.OSX_OPERATING_SYSTEM_FILTER, self.OSX_OPERATING_SYSTEM_NAME)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_comparison_card([{'module': 'Devices', 'query': WINDOWS_QUERY_NAME},
                                                 {'module': 'Users', 'query': 'Non-local users'}],
                                                self.TEST_EDIT_CHART_TITLE)
        # verify reset config
        self.dashboard_page.verify_card_config_reset_comparison_chart(self.TEST_EDIT_CHART_TITLE)

        self.dashboard_page.edit_card(self.TEST_EDIT_CHART_TITLE)
        self.dashboard_page.add_comparison_card_view('Devices', self.OSX_OPERATING_SYSTEM_NAME)

    def test_dashboard_empty_title(self):
        """
        Test empty dashboard card with no title, save won't be clickable (disabled) and will "fail" then we actually
        add title and save and it should work
        """
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_LINUX, LINUX_QUERY_NAME)
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        with pytest.raises(NoSuchElementException):
            self.dashboard_page.add_comparison_card([{'module': 'Devices', 'query': WINDOWS_QUERY_NAME},
                                                     {'module': 'Devices', 'query': LINUX_QUERY_NAME}],
                                                    '')

        assert self.dashboard_page.is_chart_save_disabled()
        # this should work after we add the title
        self.dashboard_page.fill_current_chart_title(self.TEST_EDIT_CHART_TITLE)
        assert not self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.click_card_save()

    def _test_read_only_user_with_dashboard_read_write(self):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        # Login with Admin user and change the read only Dashboard permission
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'],
                              wait_for_getting_started=True)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.wait_for_table_to_load()
        user = self.settings_page.get_user_object_by_user_name(READ_ONLY_USERNAME)
        self.settings_page.click_manage_roles_settings()
        self.settings_page.wait_for_table_to_load()
        self.settings_page.click_role_by_name(user.role)
        self.settings_page.wait_for_side_panel()
        self.settings_page.get_role_edit_panel_action().click()
        self.settings_page.select_permissions({
            'dashboard': 'all'
        })
        self.settings_page.click_save_button()
        self.settings_page.safeguard_click_confirm('Yes')
        self.settings_page.wait_for_role_successfully_saved_toaster()

        self.dashboard_page.switch_to_page()
        # Login with Read Only user and see it can see personal space and add a chart
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_ONLY_USERNAME, password=NEW_PASSWORD,
                              wait_for_getting_started=False)
        self.dashboard_page.switch_to_page()
        assert not self.dashboard_page.is_missing_space(DASHBOARD_SPACE_PERSONAL)
        self.dashboard_page.click_tab(DASHBOARD_SPACE_PERSONAL)
        assert not self.dashboard_page.is_element_disabled(self.dashboard_page.find_new_chart_card())

    def _test_dashboard_segmentation_filter(self):
        # Add empty values - expected to generate two bars (Windows and No Value)
        self.dashboard_page.edit_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        self.dashboard_page.check_chart_segment_include_empty()
        self.dashboard_page.click_card_save()
        filtered_chart = self.dashboard_page.get_histogram_chart_by_title(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        assert self.dashboard_page.get_paginator_total_num_of_items(filtered_chart) == '1'

        # Change to host and add filter 'domain' - expected to filter out the JSON device
        self.dashboard_page.edit_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        self.dashboard_page.check_chart_segment_include_empty()
        assert not self.dashboard_page.is_toggle_selected(self.dashboard_page.find_chart_segment_include_empty())
        self.dashboard_page.select_chart_wizard_field('Host Name')
        self.dashboard_page.fill_chart_segment_filter('Host Name', 'domain')
        self.dashboard_page.click_card_save()
        filtered_chart = self.dashboard_page.get_histogram_chart_by_title(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        assert self.dashboard_page.get_paginator_total_num_of_items(filtered_chart) == '21'

        # Remove the filter - expected to generate as many bars as devices
        self.dashboard_page.edit_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        self.dashboard_page.remove_chart_segment_filter()
        self.dashboard_page.click_card_save()
        filtered_chart = self.dashboard_page.get_histogram_chart_by_title(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        assert self.dashboard_page.get_paginator_total_num_of_items(filtered_chart) == '22'
