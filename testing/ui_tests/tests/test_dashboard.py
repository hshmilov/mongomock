import time
from contextlib import contextmanager
from math import ceil

import pytest
import requests
from selenium.common.exceptions import NoSuchElementException

from services.axon_service import TimeoutException
from services.adapters import stresstest_service
from axonius.consts.gui_consts import (DASHBOARD_SPACE_DEFAULT,
                                       DASHBOARD_SPACE_PERSONAL)
from axonius.utils.wait import wait_until
from axonius.entities import EntityType
from axonius.utils import datetime
from ui_tests.tests.ui_consts import (READ_WRITE_USERNAME, READ_ONLY_USERNAME, NEW_PASSWORD,
                                      FIRST_NAME, LAST_NAME, JSON_ADAPTER_NAME,
                                      STRESSTEST_ADAPTER_NAME, STRESSTEST_ADAPTER,
                                      WINDOWS_QUERY_NAME, MANAGED_DEVICES_QUERY_NAME, LINUX_QUERY_NAME)
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME


class TestDashboard(TestBase):
    UNCOVERED_QUERY = 'not (((specific_data.data.adapter_properties == "Agent") or ' \
                      '(specific_data.data.adapter_properties == "Manager")))'
    COVERED_QUERY = '((specific_data.data.adapter_properties == "Agent") ' \
                    'or (specific_data.data.adapter_properties == "Manager"))'
    SUMMARY_CARD_QUERY_DEVICES = 'specific_data.data.hostname == exists(true)'
    SUMMARY_CARD_QUERY_USERS = 'specific_data.data.logon_count == exists(true) and specific_data.data.logon_count > 0'

    IPS_192_168_QUERY = 'specific_data.data.network_interfaces.ips == regex("192.168", "i")'
    IPS_192_168_QUERY_NAME = 'IPs Subnet 192.168.0.0'
    HOSTNAME_DC_QUERY = 'specific_data.data.hostname == regex("dc", "i")'
    HOSTNAME_DC_QUERY_NAME = 'DC Devices'
    INTERSECTION_QUERY = f'({IPS_192_168_QUERY}) and ({HOSTNAME_DC_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY = f'({IPS_192_168_QUERY}) and not ({HOSTNAME_DC_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY = f'not (({IPS_192_168_QUERY}) or ({HOSTNAME_DC_QUERY}))'

    OS_WINDOWS_QUERY = 'specific_data.data.os.type == "Windows"'
    NO_OS_QUERY = 'not (specific_data.data.os.type == exists(true))'
    SEGMENTATION_PIE_CARD_QUERY = 'specific_data.data.hostname == '
    LONG_TEXT_FOR_CARD_TITLE = 'a very long chart name with more than 30 characters in the chart title'
    TEST_SUMMARY_TITLE_DEVICES = 'test summary devices'
    TEST_SUMMARY_TITLE_USERS = 'test summary users'
    TEST_INTERSECTION_TITLE = 'test intersection'
    TEST_SEGMENTATION_HISTOGRAM_TITLE = 'test segmentation histogram'
    TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM = 'test paginator on segmentation histogram - devices'
    TEST_PAGINATOR_ON_SEGMENTATION_USERS = 'test paginator on segmentation - users'
    TEST_PAGINATOR_LINKED_TO_CORRECT_FILTER = 'test paginator linked to correct filter'
    TEST_EDIT_CARD_TITLE = 'Testonius'
    SEGMENTATION_QUERY_USER_AD = 'Segmentation_User_name_AD'
    TEST_SEGMENTATION_PIE_TITLE = 'test segmentation pie'
    TEST_EDIT_CHART_TITLE = 'test edit'
    COVERAGE_SPACE_NAME = 'Coverage Dashboard'
    VULNERABILITY_SPACE_NAME = 'Vulnerability Dashboard'
    CUSTOM_SPACE_PANEL_NAME = 'Segment OS'
    PERSONAL_SPACE_PANEL_NAME = 'Private Segment OS'
    NON_EMPTY_TABLE_ROWS = '.x-table tbody tr[id]'
    EMPTY_TABLE_ROWS = '.x-table tbody tr:not([id])'
    TEST_EMPTY_TITLE = 'test empty'
    FIRST_LIFECYCLE_STAGE_TEXT = 'Fetch Devices...'
    LIFECYCLE_ADAPTER_FETCHING_STATUS = 'Fetching...'
    LIFECYCLE_ADAPTER_NOT_START_STATUS = 'Not Started'
    DEVICES_MODULE = 'Devices'
    USERS_MODULE = 'Users'
    OS_SERVICE_PACK_OPTION_NAME = 'OS: Service Pack'
    OS_TYPE_OPTION_NAME = 'OS: Type'
    NON_LOCAL_USERS_QUERY_NAME = 'Non-local users'
    AD_ADMINS_QUERY_NAME = 'AD enabled users in \'Administrators\' group'
    AD_BAD_CONFIG_QUERY_NAME = 'AD enabled users with bad configurations'
    NETWORK_IPS_OPTION_NAME = 'IPs'
    NETWORK_MAC_OPTION_NAME = 'MAC'
    MANAGED_DEVICES_OPTION_NAME = 'Managed Devices'
    NOT_LOCAL_USERS_OPTION_NAME = 'Not Local Users'
    NOT_FROM_US_USERS_OPTION_NAME = 'Users Not From US'
    AD_NO_PASSWORD_EXPIRATION_OPTION = 'AD Enabled Users Whose Password Does Not Expire'
    AD_CRITICAL_USERS_OPTION_NAME = 'AD Enabled Critical Users'
    IS_ADMIN_OPTION_NAME = 'Is Admin'
    IS_LOCAL_OPTION_NAME = 'Is Local'
    USER_NAME_OPTION_NAME = 'User Name'
    AD_PRIMARY_GROUP_ID_OPTION_NAME = 'AD Primary group ID'
    COUNT_OPTION_NAME = 'Count'
    AVERAGE_OPTION_NAME = 'Average'
    PIE_CHART_TYPE = 'pie'
    HISTOGRAM_CHART_TYPE = 'histogram'
    SUMMARY_CHART_TYPE = 'summary'
    TIMELINE_CHART_TYPE = 'timeline'
    TEST_TIMELINE_SVG_CSS = 'svg[aria-label="A chart."] g:nth-child(4) g:nth-child(2) g:nth-child(2) path'

    OSX_OPERATING_SYSTEM_NAME = 'OS X Operating System'
    OSX_OPERATING_SYSTEM_FILTER = 'specific_data.data.os.type == "OS X"'

    @pytest.mark.skip('TBD')
    def test_system_empty_state(self):
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_show_me_how_button()
        assert self.dashboard_page.find_see_all_message()
        self.dashboard_page.assert_congratulations_message_found()

    def test_dashboard_read_only_user_pagination(self):
        """
        Tests pagination in dashboard with read only user
        Tests Issue: https://axonius.atlassian.net/browse/AX-5155
        """
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self._create_get_paginator_segmentation_card(run_discovery=False,
                                                     module='Devices',
                                                     field='Host Name',
                                                     title=self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM,
                                                     view_name='')
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(READ_WRITE_USERNAME, NEW_PASSWORD,
                                           FIRST_NAME, LAST_NAME,
                                           role_name=self.settings_page.ADMIN_ROLE)
        self.settings_page.create_new_user(READ_ONLY_USERNAME, NEW_PASSWORD,
                                           FIRST_NAME, LAST_NAME,
                                           role_name=self.settings_page.READ_ONLY_ROLE)
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_WRITE_USERNAME, password=NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_card_spinner_to_end()
        # Give it some extra time to load since the wait isn't usually enough
        self.settings_page.switch_to_page()
        self.dashboard_page.switch_to_page()
        # fetch chart again since all elements will be stale from relog
        segmentation_card = self.dashboard_page.get_card(self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM)
        # create reference to the histogram within the card
        histograms_chart = self.dashboard_page.get_histogram_chart_from_card(segmentation_card)
        limit = int(self.dashboard_page.get_paginator_num_of_items(histograms_chart))
        total_num_of_items = int(self.dashboard_page.get_paginator_total_num_of_items(histograms_chart))
        # calculate the total number of pages in Paginator
        # by this way we ensure to have the exact num of pages and cover all the cases even if the
        # total_num_of_items % limit has a remainder (round up the result)
        num_of_pages = ceil(total_num_of_items / limit)
        # iterate incrementally on all the pages (next)
        for page_number in range(1, num_of_pages + 1):
            if page_number == 1:
                self.dashboard_page.click_to_next_page(histograms_chart)
            elif page_number == num_of_pages:
                break
            else:
                self.dashboard_page.click_to_next_page(histograms_chart)

    def test_dashboard_segmentation_clickable(self):
        """
        Tests Link from pages filter data correctly
        Tests Issue: https://axonius.atlassian.net/browse/AX-5150
        """
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        histograms_chart = self._create_get_paginator_segmentation_card(
            run_discovery=False,
            module='Devices',
            field='Host Name',
            title=self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM,
            view_name='')
        # create reference to the histogram within the card
        value = self.dashboard_page.get_histogram_items_title_on_pagination(histograms_chart)[0]
        self.dashboard_page.get_histogram_line_from_histogram(histograms_chart, 1).click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.get_table_count() == 1
        assert value in self.devices_page.find_search_value()

    def test_dashboard_field_segmentation(self):
        """
        Tests changing "segment by" in field segmentation chart cleans value instead of [Deleted] (that was the bug)
        Tests Issue: https://axonius.atlassian.net/browse/AX-4962
        """
        self.dashboard_page.switch_to_page()
        self.dashboard_page.open_new_card_wizard()
        self.dashboard_page.select_chart_metric('Field Segmentation')
        self.dashboard_page.select_chart_wizard_module(self.DEVICES_MODULE)
        self.dashboard_page.select_chart_wizard_adapter(AD_ADAPTER_NAME)
        self.dashboard_page.select_chart_wizard_field(self.AD_PRIMARY_GROUP_ID_OPTION_NAME)
        value = self.dashboard_page.get_chart_wizard_field_value().lower()
        assert value == self.AD_PRIMARY_GROUP_ID_OPTION_NAME.lower()
        # Json adapter doesn't have AD PRIMARY GROUP so it switches to ID in future fix it needs to be also empty
        # i.e act like changing to general
        self.dashboard_page.select_chart_wizard_adapter(JSON_ADAPTER_NAME)
        assert self.dashboard_page.get_chart_wizard_field_value() == 'ID'
        self.dashboard_page.select_chart_wizard_adapter(self.devices_page.VALUE_ADAPTERS_GENERAL)
        try:
            self.dashboard_page.get_chart_wizard_field_value()
        except NoSuchElementException:
            pass
        # Switch when both adapters have the field type won't delete or change
        self.dashboard_page.select_chart_wizard_adapter(AD_ADAPTER_NAME)
        self.dashboard_page.select_chart_wizard_field('Host Name')
        assert self.dashboard_page.get_chart_wizard_field_value() == 'Host Name'
        self.dashboard_page.select_chart_wizard_adapter(JSON_ADAPTER_NAME)
        assert self.dashboard_page.get_chart_wizard_field_value() == 'Host Name'

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
            self.dashboard_page.add_comparison_card('Devices',
                                                    WINDOWS_QUERY_NAME,
                                                    'Devices',
                                                    LINUX_QUERY_NAME,
                                                    '')

        assert self.dashboard_page.is_chart_save_disabled()
        # this should work after we add the title
        self.dashboard_page.fill_current_chart_title(self.TEST_EDIT_CHART_TITLE)
        assert not self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.click_card_save()

    def test_dashboard_sanity(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()

        # Allow the caches to be rebuilt
        time.sleep(5)

        # This triggers a dashboard reload
        self.settings_page.switch_to_page()
        self.dashboard_page.switch_to_page()

        mdc_card = self.dashboard_page.find_managed_device_coverage_card()
        assert self.dashboard_page.get_title_from_card(mdc_card) == self.dashboard_page.MANAGED_DEVICE_COVERAGE
        mdc_pie = self.dashboard_page.get_pie_chart_from_card(mdc_card)
        # currently it's 95 covered and 5 uncovered, but it might change in the future
        covered = self.dashboard_page.get_covered_from_pie(mdc_pie)
        assert covered > 80
        uncovered = self.dashboard_page.get_uncovered_from_pie(mdc_pie)
        assert uncovered < 20
        assert covered + uncovered == 100
        sl_card = self.dashboard_page.find_system_lifecycle_card()
        assert self.dashboard_page.get_title_from_card(sl_card) == self.dashboard_page.SYSTEM_LIFECYCLE
        sl_cycle = self.dashboard_page.get_cycle_from_card(sl_card)
        self.dashboard_page.assert_check_in_cycle(sl_cycle)
        self.dashboard_page.assert_cycle_is_stable(sl_cycle)
        self.dashboard_page.assert_cycle_start_and_finish_dates(sl_card)

        nc_card = self.dashboard_page.find_new_chart_card()
        assert self.dashboard_page.get_title_from_card(nc_card) == self.dashboard_page.NEW_CHART
        self.dashboard_page.assert_plus_button_in_card(nc_card)

        dd_card = self.dashboard_page.find_device_discovery_card()
        assert self.dashboard_page.get_title_from_card(dd_card) == self.dashboard_page.DEVICE_DISCOVERY
        self.dashboard_page.find_adapter_in_card(dd_card, 'active_directory_adapter')
        self.dashboard_page.find_adapter_in_card(dd_card, 'json_file_adapter')
        quantities = self.dashboard_page.find_quantity_in_card(dd_card)
        assert quantities[0] + quantities[1] == quantities[2]
        assert quantities[2] >= quantities[3]

        ud_card = self.dashboard_page.find_user_discovery_card()
        assert self.dashboard_page.get_title_from_card(ud_card) == self.dashboard_page.USER_DISCOVERY
        self.dashboard_page.find_adapter_in_card(ud_card, 'active_directory_adapter')
        self.dashboard_page.find_adapter_in_card(ud_card, 'json_file_adapter')
        quantities = self.dashboard_page.find_quantity_in_card(ud_card)
        assert quantities[0] + quantities[1] == quantities[2]
        assert quantities[2] >= quantities[3]

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
        self.devices_page.create_saved_query(self.IPS_192_168_QUERY, self.IPS_192_168_QUERY_NAME)
        self.devices_page.create_saved_query(self.HOSTNAME_DC_QUERY, self.HOSTNAME_DC_QUERY_NAME)
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_intersection_card('Devices',
                                                  self.IPS_192_168_QUERY_NAME,
                                                  self.HOSTNAME_DC_QUERY_NAME,
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

    def _create_get_paginator_segmentation_card(self, run_discovery, module, field, title, view_name):
        self.dashboard_page.switch_to_page()
        if run_discovery:
            self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card(module=module,
                                                  field=field,
                                                  title=title,
                                                  view_name=view_name,
                                                  partial_text=False)
        # create reference to the segmentation card with title
        segmentation_card = self.dashboard_page.get_card(title)
        # create reference to the histogram within the card
        return self.dashboard_page.get_histogram_chart_from_card(segmentation_card)

    def _test_paginator_state_first_page(self, histograms_chart, page_number, to_val):
        assert not self.dashboard_page.is_missing_paginator_num_of_items(histograms_chart)
        assert self.dashboard_page.is_missing_paginator_from_item(histograms_chart)
        assert self.dashboard_page.is_missing_paginator_to_item(histograms_chart)
        assert int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number)) == to_val
        assert self.dashboard_page.check_paginator_buttons_state(histograms_chart, True, True, False, False)

    def _test_paginator_state_middle_page(self, histograms_chart, page_number, to_val, from_val):
        assert self.dashboard_page.is_missing_paginator_num_of_items(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_from_item(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_to_item(histograms_chart)
        assert self.dashboard_page.check_paginator_buttons_state(histograms_chart, False, False, False, False)
        assert int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number)) == to_val
        assert int(self.dashboard_page.get_paginator_from_item_number(histograms_chart)) == from_val

    def _test_paginator_state_last_page(self, histograms_chart, page_number, to_val, from_val):
        assert self.dashboard_page.is_missing_paginator_num_of_items(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_from_item(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_to_item(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_from_item(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_to_item(histograms_chart)
        assert int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number)) == to_val
        assert int(self.dashboard_page.get_paginator_from_item_number(histograms_chart)) == from_val
        assert self.dashboard_page.check_paginator_buttons_state(histograms_chart, False, False, True, True)

    @staticmethod
    def _check_num_of_histograms_items_fit_paginator_number(page_number, num_of_pages, num_of_histogram_lines,
                                                            num_of_items, total_num_of_items, limit):
        # num_of_items: it represents the number of items that we reached on the current page...
        #               it is the so called "TO" number in the pagination"
        # if number of histogram items fit the "To" value of the Paginator
        if page_number != num_of_pages:
            # in case we are not in the last page we expect the num_of_histogram_lines to fit
            # the num_of_items divided by the current page number
            assert num_of_histogram_lines == num_of_items / page_number
        else:
            # in case we are in last page we expect the num_of_histogram_lines to be:
            # the reminder of total_num_of_items % limit
            # if total_num_of_items != limit == 0
            # otherwise should as in previous case
            if total_num_of_items % limit == 0:
                assert num_of_histogram_lines == num_of_items / page_number
            else:
                assert num_of_histogram_lines == total_num_of_items % limit

    def _gather_paginator_iteration_data(self, histograms_chart, page_number, num_of_pages, total_num_of_items,
                                         limit):
        num_of_histogram_lines = self.dashboard_page.get_count_histogram_lines_from_histogram(histograms_chart)
        num_of_items = int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number))
        # calculate Paginator 'To' value
        to_val = self.dashboard_page.calculate_to_item_value(num_of_items, page_number, limit)
        # calculate Paginator 'From' value
        from_val = self.dashboard_page.calculate_from_item_value(num_of_items, num_of_pages,
                                                                 page_number, to_val, limit)
        return num_of_histogram_lines, num_of_items, to_val, from_val

    def grab_all_host_names_from_devices(self):
        self.devices_page.switch_to_page()
        self.devices_page.select_page_size(50)
        return self.devices_page.get_column_data_slicer(self.devices_page.FIELD_HOSTNAME_TITLE)

    @staticmethod
    def assert_data_devices_fit_pagination_data(histogram_items_title, host_names_list):
        # Checking the lists are equal by one sided containment + equal length
        assert len(histogram_items_title) == len(host_names_list)
        assert all(item in host_names_list for item in histogram_items_title)

    def generate_csv_from_segmentation_graph(self, panel_id):
        session = requests.Session()
        cookies = self.driver.get_cookies()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        return session.get(f'https://127.0.0.1/api/dashboards/panels/{panel_id}/csv')

    def grab_all_host_names_from_csv(self, panel_id):
        result = self.generate_csv_from_segmentation_graph(panel_id)
        all_csv_rows = result.content.decode('utf-8').split('\r\n')
        csv_data_rows = all_csv_rows[1:-1]
        return [str.split(',')[0] for str in csv_data_rows]

    def get_segmentation_card_id(self):
        segmentation_card = self.dashboard_page.get_card(self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM)
        card_id = segmentation_card.get_property('id')
        return card_id

    def test_check_segmentation_csv(self):
        histogram_items_title = []
        histograms_chart = \
            self._create_get_paginator_segmentation_card(run_discovery=True,
                                                         module='Devices',
                                                         field='Host Name',
                                                         title=self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM,
                                                         view_name='')
        panel_id = self.get_segmentation_card_id()
        limit = int(self.dashboard_page.get_paginator_num_of_items(histograms_chart))
        total_num_of_items = int(self.dashboard_page.get_paginator_total_num_of_items(histograms_chart))
        # calculate the total number of pages in Paginator
        # by this wat we ensure to have the exact num of pages and cover all the cases even if the
        # total_num_of_items % limit has a remainder (round up the result)
        num_of_pages = ceil(total_num_of_items / limit)
        # iterate incrementaly on all the pages (next)
        for page_number in range(1, num_of_pages + 1):
            histogram_items_title.append(self.dashboard_page.get_histogram_items_title_on_pagination(histograms_chart))
            if page_number == 1:
                self.dashboard_page.click_to_next_page(histograms_chart)
            elif page_number == num_of_pages:
                break
            else:
                self.dashboard_page.click_to_next_page(histograms_chart)
        # flatten list
        histogram_titles_list = [item for sublist in histogram_items_title for item in sublist]
        host_names_list = self.grab_all_host_names_from_csv(panel_id)
        # compare histograms_item_titles of pagination with data grabbed from devices table
        self.assert_data_devices_fit_pagination_data(histogram_titles_list, host_names_list)
        self.dashboard_page.remove_card(self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM)

    def test_paginator_paginator_update_after_discovery(self):
        self.users_page.switch_to_page()
        self.base_page.run_discovery()
        wait_until(lambda: self.devices_queries_page.get_table_count() > 0)
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.users_page.select_query_adapter(JSON_ADAPTER_NAME)
        self.devices_page.toggle_not(expressions[0])
        self.users_page.click_search()
        self.users_page.wait_for_table_to_load()
        self.users_page.click_save_query()
        self.users_page.fill_query_name(self.SEGMENTATION_QUERY_USER_AD)
        self.users_page.click_save_query_save_button()
        first_result_count = self.users_page.count_entities()
        self.users_page.click_row_checkbox(1)
        self.users_page.click_row_checkbox(2)
        self.users_page.click_row_checkbox(3)
        self.users_page.open_delete_dialog()
        self.users_page.confirm_delete()
        self.users_page.wait_for_table_to_load()
        second_result_count = self.users_page.count_entities()
        assert second_result_count == first_result_count - 3
        histograms_chart = \
            self._create_get_paginator_segmentation_card(run_discovery=False,
                                                         module='Users',
                                                         field='User Name',
                                                         title=self.TEST_PAGINATOR_ON_SEGMENTATION_USERS,
                                                         view_name=self.SEGMENTATION_QUERY_USER_AD)
        # verify reset chart
        self.dashboard_page.verify_card_config_reset_segmentation_chart(self.TEST_PAGINATOR_ON_SEGMENTATION_USERS)

        total_num_of_items = int(self.dashboard_page.get_paginator_total_num_of_items(histograms_chart))
        assert total_num_of_items == second_result_count
        self.base_page.run_discovery()
        wait_until(lambda: int(
            self.dashboard_page.get_paginator_total_num_of_items(
                self.dashboard_page.get_card(self.TEST_PAGINATOR_ON_SEGMENTATION_USERS))) == first_result_count)
        self.dashboard_page.remove_card(self.TEST_PAGINATOR_ON_SEGMENTATION_USERS)

    def test_multi_page_histogram_linked_to_correct_filter(self):
        histograms_chart = \
            self._create_get_paginator_segmentation_card(run_discovery=True,
                                                         module='Devices',
                                                         field='Host Name',
                                                         title=self.TEST_PAGINATOR_LINKED_TO_CORRECT_FILTER,
                                                         view_name='')
        # on First Page
        selected_item_bart_title = self.dashboard_page.get_histogram_bar_item_title(histograms_chart, 1)
        self.dashboard_page.click_on_histogram_item(histograms_chart, 1)
        # assert that the query is correct
        assert self.devices_page.find_query_search_input().get_attribute('value') == \
            f'specific_data.data.hostname == "{selected_item_bart_title}"'
        self.dashboard_page.switch_to_page()
        # create reference to the histogram within the card
        segmentation_card = self.dashboard_page.get_card(self.TEST_PAGINATOR_LINKED_TO_CORRECT_FILTER)
        # set focus back on the histogram chart (after switching page)
        histograms_chart = self.dashboard_page.get_histogram_chart_from_card(segmentation_card)
        # Got to Last Page
        self.dashboard_page.click_to_last_page(histograms_chart)
        selected_item_bart_title = self.dashboard_page.get_histogram_bar_item_title(histograms_chart, 1)
        self.dashboard_page.click_on_histogram_item(histograms_chart, 1)
        # assert that the query is correct
        assert self.devices_page.find_query_search_input().get_attribute('value') == \
            f'specific_data.data.hostname == "{selected_item_bart_title}"'
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_card(self.TEST_PAGINATOR_LINKED_TO_CORRECT_FILTER)

    def test_paginator_on_segmentation_chart(self):
        histogram_items_title = []
        histograms_chart = self._create_get_paginator_segmentation_card(
            run_discovery=True,
            module='Devices',
            field='Host Name',
            title=self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM,
            view_name='')
        assert not self.dashboard_page.is_missing_paginator_navigation(histograms_chart)
        limit = int(self.dashboard_page.get_paginator_num_of_items(histograms_chart))
        total_num_of_items = int(self.dashboard_page.get_paginator_total_num_of_items(histograms_chart))
        # calculate the total number of pages in Paginator
        # by this wat we ensure to have the exact num of pages and cover all the cases even if the
        # total_num_of_items % limit has a remainder ((round up the result)
        num_of_pages = ceil(total_num_of_items / limit)
        # iterate incrementaly on all the pages (next)
        for page_number in range(1, num_of_pages + 1):
            num_of_histogram_lines, num_of_items, to_val, from_val = \
                self._gather_paginator_iteration_data(histograms_chart, page_number, num_of_pages,
                                                      total_num_of_items, limit)
            self._check_num_of_histograms_items_fit_paginator_number(page_number, num_of_pages,
                                                                     num_of_histogram_lines,
                                                                     num_of_items,
                                                                     total_num_of_items,
                                                                     limit)
            if page_number == 1:
                self._test_paginator_state_first_page(histograms_chart, page_number, to_val)
                self.dashboard_page.click_to_next_page(histograms_chart)
            elif page_number == num_of_pages:
                self._test_paginator_state_last_page(histograms_chart, page_number, to_val,
                                                     from_val)
            else:
                self._test_paginator_state_middle_page(histograms_chart, page_number, to_val,
                                                       from_val)
                self.dashboard_page.click_to_next_page(histograms_chart)
        # iterate decrementaly on all the  pages (back)
        for page_number in range(num_of_pages, 0, -1):
            num_of_histogram_lines, num_of_items, to_val, from_val = \
                self._gather_paginator_iteration_data(histograms_chart, page_number, num_of_pages,
                                                      total_num_of_items, limit)
            self._check_num_of_histograms_items_fit_paginator_number(page_number, num_of_pages,
                                                                     num_of_histogram_lines,
                                                                     num_of_items,
                                                                     total_num_of_items,
                                                                     limit)
            histogram_items_title.append(self.dashboard_page.get_histogram_items_title_on_pagination(histograms_chart))
            if page_number == 1:
                self._test_paginator_state_first_page(histograms_chart, page_number, to_val)
            elif page_number == num_of_pages:
                self._test_paginator_state_last_page(histograms_chart, page_number, to_val, from_val)
                self.dashboard_page.click_to_previous_page(histograms_chart)
            else:
                self._test_paginator_state_middle_page(histograms_chart, page_number, to_val, from_val)
                self.dashboard_page.click_to_previous_page(histograms_chart)
        # flatten list
        histogram_titles_list = [item for sublist in histogram_items_title for item in sublist]
        devices_tiles_list = self.grab_all_host_names_from_devices()
        self.assert_data_devices_fit_pagination_data(histogram_titles_list, devices_tiles_list)
        self.dashboard_page.switch_to_page()
        # create reference to the histogram within the card
        segmentation_card = self.dashboard_page.get_card(self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM)
        # set focus back on the histogram chart (after switching page)
        histograms_chart = self.dashboard_page.get_histogram_chart_from_card(segmentation_card)
        # Got to Last Page
        page_number = num_of_pages
        self.dashboard_page.click_to_last_page(histograms_chart)
        num_of_items = int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number))
        # calculate Paginator 'To' value
        to_val = self.dashboard_page.calculate_to_item_value(num_of_items, page_number, limit)
        # calculate Paginator 'From' value
        from_val = self.dashboard_page.calculate_from_item_value(num_of_items, num_of_pages,
                                                                 page_number, to_val, limit)
        self._test_paginator_state_last_page(histograms_chart, page_number, to_val, from_val)
        # Go to First Page
        page_number = 1
        self.dashboard_page.click_to_first_page(histograms_chart)
        num_of_items = int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number))
        # calculate Paginator 'To' value
        to_val = self.dashboard_page.calculate_to_item_value(num_of_items, page_number, limit)
        self._test_paginator_state_first_page(histograms_chart, page_number, to_val)
        self.dashboard_page.remove_card(self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM)

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

    def test_dashboard_segmentation_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card(
            'Devices', self.OS_TYPE_OPTION_NAME, self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        # verify config reset
        self.dashboard_page.verify_card_config_reset_segmentation_chart(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        shc_card = self.dashboard_page.get_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        shc_chart = self.dashboard_page.get_histogram_chart_from_card(shc_card)
        line = self.dashboard_page.get_histogram_line_from_histogram(shc_chart, 1)
        first_result_count = int(line.text)
        line.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == first_result_count
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

    def _does_user_appear(self):
        results = self.dashboard_page.get_all_table_rows()
        return len(results) > 1 and results[1]

    def test_dashboard_search(self):
        string_to_search = 'be'
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.fill_query_value(string_to_search)
        self.dashboard_page.enter_search()
        self.dashboard_page.wait_for_table_to_load()
        wait_until(self._does_user_appear)
        results = self.dashboard_page.get_all_table_rows()
        host_name = results[0][0]
        user_name = results[1][0]
        tables_count = self.dashboard_page.get_all_tables_counters()
        dashboard_devices_table_count = tables_count[0]
        dashboard_users_table_count = tables_count[1]
        assert len(results) == dashboard_devices_table_count + dashboard_users_table_count
        for result in results:
            assert any(string_to_search in s.lower() for s in result)
        self.dashboard_page.open_view_devices()
        wait_until(lambda: 'devices' in self.driver.current_url)
        self.devices_page.wait_for_table_to_load()
        devices_page_tables_count = self.devices_page.get_all_tables_counters()[0]
        assert devices_page_tables_count == dashboard_devices_table_count
        assert self.devices_page.find_search_value() == string_to_search
        assert any(host_name in s for s in self.devices_page.get_all_table_rows()[0])
        self.devices_page.page_back()
        self.dashboard_page.open_view_users()
        wait_until(lambda: 'users' in self.driver.current_url)
        self.users_page.wait_for_table_to_load()
        users_tables_count = self.users_page.get_all_tables_counters()[0]
        assert users_tables_count == dashboard_users_table_count
        assert self.users_page.find_search_value() == string_to_search
        assert any(user_name in s for s in self.users_page.get_all_table_rows()[0])
        self.users_page.page_back()
        self.dashboard_page.wait_for_table_to_load()
        device_id = self.devices_page.find_first_id()
        self.devices_page.click_row()
        self.devices_page.wait_for_spinner_to_end()
        assert device_id in self.driver.current_url
        hostname = self.devices_page.get_value_for_label_in_device_page(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert hostname == 'EC2AMAZ-61GTBER.TestDomain.test'

    def test_dashboard_search_url(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.driver.get(f'{self.driver.current_url}dashboard/explorer?search=dc')
        self.dashboard_page.wait_for_table_to_load()
        wait_until(self._does_user_appear)
        assert self.dashboard_page.get_all_tables_counters() == [4, 0]

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
        self.dashboard_page.add_segmentation_card('Devices', self.OS_TYPE_OPTION_NAME, self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.wait_for_spinner_to_end()
        segment_card = self.dashboard_page.get_card(self.CUSTOM_SPACE_PANEL_NAME)
        assert segment_card and self.dashboard_page.get_histogram_chart_from_card(segment_card)
        self.dashboard_page.find_space_header(1).click()
        assert self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.find_space_header(2).click()
        assert self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)

        # Add a panel to the Personal space and check hidden from other user
        self.dashboard_page.add_segmentation_card('Devices', self.OS_TYPE_OPTION_NAME, self.PERSONAL_SPACE_PANEL_NAME)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(READ_WRITE_USERNAME, NEW_PASSWORD,
                                           FIRST_NAME, LAST_NAME,
                                           role_name=self.settings_page.ADMIN_ROLE)
        self.settings_page.create_new_user(READ_ONLY_USERNAME, NEW_PASSWORD,
                                           FIRST_NAME, LAST_NAME,
                                           role_name=self.settings_page.READ_ONLY_ROLE)
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

    def test_dashboard_edit_module(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.create_saved_query(self.OSX_OPERATING_SYSTEM_FILTER, self.OSX_OPERATING_SYSTEM_NAME)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_comparison_card('Devices', WINDOWS_QUERY_NAME,
                                                'Users', 'Non-local users',
                                                self.TEST_EDIT_CHART_TITLE)
        # verify reset config
        self.dashboard_page.verify_card_config_reset_comparison_chart(self.TEST_EDIT_CHART_TITLE)

        self.dashboard_page.edit_card(self.TEST_EDIT_CHART_TITLE)
        self.dashboard_page.add_comparison_card_view('Devices', self.OSX_OPERATING_SYSTEM_NAME)

    def test_dashboard_empty_segmentation_chart(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.OSX_OPERATING_SYSTEM_FILTER, self.OSX_OPERATING_SYSTEM_NAME)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card(module='Devices',
                                                  field=self.OS_TYPE_OPTION_NAME,
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
        self.dashboard_page.add_comparison_card(first_module='Devices',
                                                first_query=self.OSX_OPERATING_SYSTEM_NAME,
                                                second_module='Devices',
                                                second_query=self.OSX_OPERATING_SYSTEM_NAME,
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

    def _test_query_default_chart(self, default_chart, table_state):
        self.devices_queries_page.switch_to_page()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_queries_page.fill_enter_table_search(default_chart['query_name'])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_queries_page.find_query_row_by_name(default_chart['query_name']).click()
        self.devices_queries_page.run_query()
        assert 'devices' in self.driver.current_url and 'query' not in self.driver.current_url
        self.devices_page.wait_for_spinner_to_end()
        self.driver.find_element_by_css_selector(table_state)
        self.dashboard_page.switch_to_page()

    def test_default_charts_with_no_results_are_not_shown(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        default_charts_meta = [{
            'title': self.dashboard_page.MANAGED_DEVICE_COVERAGE,
            'query_name': MANAGED_DEVICES_QUERY_NAME
        }, {
            'title': self.dashboard_page.VA_SCANNER_COVERAGE,
            'query_name': 'Scanned by VA'
        }, {
            'title': self.dashboard_page.ENDPOINT_PROTECTION_COVERAGE,
            'query_name': 'Protected endpoints'
        }]
        for default_chart in default_charts_meta:
            try:
                self.dashboard_page.get_card(default_chart['title'])
                self._test_query_default_chart(default_chart, self.NON_EMPTY_TABLE_ROWS)
            except (TimeoutException, NoSuchElementException):
                self._test_query_default_chart(default_chart, self.EMPTY_TABLE_ROWS)

    def test_dashboard_lifecycle_tooltip(self):
        self.dashboard_page.switch_to_page()
        # during the first time discovery there is no lifecycle card
        self.base_page.run_discovery(True)
        stress = stresstest_service.StresstestService()
        with stress.contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(STRESSTEST_ADAPTER_NAME)
            # using fetch_device_interval will enforce fetching time for each device
            # in this configuration expected time to run is 60 x 1 seconds
            device_dict = {'device_count': 60, 'name': 'testonius', 'fetch_device_interval': 1}
            self.adapters_page.add_server(device_dict, STRESSTEST_ADAPTER_NAME)
            self.adapters_page.wait_for_server_green()
            self.dashboard_page.switch_to_page()
            # during the second time discovery there is lifecycle card
            # no need to wait for discovery to end
            self.base_page.run_discovery(False)
            self.dashboard_page.wait_for_element_present_by_text(self.FIRST_LIFECYCLE_STAGE_TEXT)
            self.dashboard_page.hover_over_lifecycle_chart()
            # get all data from tooltip table
            table_data = self.dashboard_page.get_lifecycle_tooltip_table_data()
            # check the status of stress adapter
            stress_adapters_found = False
            for row in table_data:
                # check for name and available statuses, if status isn't in the list something is wrong
                if row.get('name') == STRESSTEST_ADAPTER_NAME and \
                        row.get('status') in [self.LIFECYCLE_ADAPTER_FETCHING_STATUS,
                                              self.LIFECYCLE_ADAPTER_NOT_START_STATUS]:
                    stress_adapters_found = True

            assert stress_adapters_found
            # wait for discovery to end, can`t clean servers or remove adapter while discovery cycle running
            self.base_page.wait_for_run_research()
            self.adapters_page.clean_adapter_servers(STRESSTEST_ADAPTER_NAME)
            self.wait_for_adapter_down(STRESSTEST_ADAPTER)

    def test_dashboard_lifecycle_next_cycle(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()

        # This triggers a dashboard reload
        self.settings_page.switch_to_page()
        self.settings_page.fill_schedule_rate('0.1')
        self.settings_page.save_and_wait_for_toaster()

        self.dashboard_page.switch_to_page()

        sl_card = self.dashboard_page.find_system_lifecycle_card()
        assert self.dashboard_page.get_title_from_card(sl_card) == self.dashboard_page.SYSTEM_LIFECYCLE

        self.dashboard_page.wait_for_element_present_by_text('6 minutes', sl_card)

        self.dashboard_page.wait_for_element_present_by_text('Less than 1 minute', sl_card, interval=12)

        self.dashboard_page.wait_for_element_present_by_text('6 minutes', sl_card, interval=6)

    @contextmanager
    def _edit_and_assert_chart(self, card, assert_data, chart_type=PIE_CHART_TYPE):
        self.dashboard_page.edit_card(self.TEST_EDIT_CARD_TITLE)
        yield
        self.dashboard_page.click_card_save()
        if chart_type == self.PIE_CHART_TYPE:
            self.dashboard_page.assert_pie_slices_data(card, assert_data)
        if chart_type == self.HISTOGRAM_CHART_TYPE:
            self.dashboard_page.assert_histogram_lines_data(card, assert_data)
        if chart_type == self.SUMMARY_CHART_TYPE:
            self.dashboard_page.assert_summary_text_data(card, assert_data)
        if chart_type == self.TIMELINE_CHART_TYPE:
            self.dashboard_page.assert_timeline_svg_exist(card, assert_data)

    def test_dashboard_chart_edit(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.create_saved_query(self.HOSTNAME_DC_QUERY, self.HOSTNAME_DC_QUERY_NAME)
        self.devices_page.create_saved_query(self.IPS_192_168_QUERY, self.IPS_192_168_QUERY_NAME)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_intersection_card(module=self.DEVICES_MODULE,
                                                  first_query=WINDOWS_QUERY_NAME,
                                                  second_query=MANAGED_DEVICES_QUERY_NAME,
                                                  title=self.TEST_EDIT_CARD_TITLE)
        card = self.dashboard_page.find_dashboard_card(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_pie_slices_data(card, ['5', '91', '5'])
        self._test_intersection_chart_edit(card)
        self._change_card_to_comparison(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_pie_slices_data(card, ['83', '17'])
        self._test_comparison_chart_edit(card)
        self._change_card_to_segmentation(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_histogram_lines_data(card, ['2', '1'])
        self._test_segmentation_chart_edit(card)
        self._change_card_to_summary(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_summary_text_data(card, ['20'])
        self._test_summary_chart_edit(card)
        self._change_card_to_timeline(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_timeline_svg_exist(card, self.TEST_TIMELINE_SVG_CSS)
        self._test_timeline_chart_edit(card)

    def _change_card_to_comparison(self, title):
        self.dashboard_page.edit_card(title)
        self.dashboard_page.select_chart_metric('Query Comparison')
        assert self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.change_chart_type(self.PIE_CHART_TYPE)
        views_list = self.dashboard_page.get_views_list()
        self.dashboard_page.select_chart_wizard_module(self.DEVICES_MODULE, views_list[0])
        self.dashboard_page.select_chart_view_name(WINDOWS_QUERY_NAME, views_list[0])
        self.dashboard_page.select_chart_wizard_module(self.DEVICES_MODULE, views_list[1])
        self.dashboard_page.select_chart_view_name(self.HOSTNAME_DC_QUERY_NAME, views_list[1])
        self.dashboard_page.click_card_save()

    def _change_card_to_segmentation(self, title):
        self.dashboard_page.edit_card(title)
        self.dashboard_page.select_chart_metric('Field Segmentation')
        assert self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.change_chart_type(self.HISTOGRAM_CHART_TYPE)
        self.dashboard_page.select_chart_wizard_module(self.DEVICES_MODULE)
        self.dashboard_page.select_chart_view_name(WINDOWS_QUERY_NAME)
        self.dashboard_page.select_chart_wizard_field(self.OS_SERVICE_PACK_OPTION_NAME)
        self.dashboard_page.click_card_save()

    def _change_card_to_summary(self, title):
        self.dashboard_page.edit_card(title)
        self.dashboard_page.select_chart_metric('Field Summary')
        assert self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.select_chart_wizard_module(self.DEVICES_MODULE)
        self.dashboard_page.select_chart_wizard_field(self.OS_TYPE_OPTION_NAME)
        self.dashboard_page.select_chart_summary_function(self.COUNT_OPTION_NAME)
        self.dashboard_page.click_card_save()

    def _change_card_to_timeline(self, title):
        self._create_history(EntityType.Devices)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.edit_card(title)
        self.dashboard_page.select_chart_metric('Query Timeline')
        assert self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.select_chart_wizard_module(self.DEVICES_MODULE)
        self.dashboard_page.select_chart_view_name(WINDOWS_QUERY_NAME)
        self.dashboard_page.select_chart_result_range_last()
        self.dashboard_page.click_card_save()

    def _test_intersection_chart_edit(self, card):
        with self._edit_and_assert_chart(card, ['5', '18', '77'], self.PIE_CHART_TYPE):
            self.dashboard_page.select_intersection_chart_first_query(self.HOSTNAME_DC_QUERY_NAME)

        with self._edit_and_assert_chart(card, ['9', '18', '73'], self.PIE_CHART_TYPE):
            self.dashboard_page.select_intersection_chart_second_query(WINDOWS_QUERY_NAME)

        with self._edit_and_assert_chart(card, ['53', '47'], self.PIE_CHART_TYPE):
            self.dashboard_page.select_chart_wizard_module(self.USERS_MODULE)
            self.dashboard_page.select_intersection_chart_first_query(self.NON_LOCAL_USERS_QUERY_NAME)
            self.dashboard_page.select_intersection_chart_second_query(self.AD_ADMINS_QUERY_NAME)

        with self._edit_and_assert_chart(card, ['60', '40'], self.PIE_CHART_TYPE):
            self.dashboard_page.select_intersection_chart_second_query(self.AD_BAD_CONFIG_QUERY_NAME)

        with self._edit_and_assert_chart(card, ['33', '27', '20', '20'], self.PIE_CHART_TYPE):
            self.dashboard_page.select_intersection_chart_first_query(self.AD_ADMINS_QUERY_NAME)

    def _test_comparison_chart_edit(self, card):
        with self._edit_and_assert_chart(card, ['51', '49'], self.PIE_CHART_TYPE):
            views_list = self.dashboard_page.get_views_list()
            self.dashboard_page.select_chart_view_name(MANAGED_DEVICES_QUERY_NAME, views_list[1])

        with self._edit_and_assert_chart(card, ['21', '20'], self.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.change_chart_type(self.HISTOGRAM_CHART_TYPE)

        with self._edit_and_assert_chart(card, ['20', '15'], self.HISTOGRAM_CHART_TYPE):
            views_list = self.dashboard_page.get_views_list()
            self.dashboard_page.select_chart_wizard_module(self.USERS_MODULE, views_list[1])
            self.dashboard_page.select_chart_view_name(self.NON_LOCAL_USERS_QUERY_NAME, views_list[1])

    def _test_segmentation_chart_edit(self, card):
        with self._edit_and_assert_chart(card, ['2'], self.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.fill_chart_segment_filter(self.OS_SERVICE_PACK_OPTION_NAME, '1')

        with self._edit_and_assert_chart(card, ['7', '1'], self.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.select_chart_wizard_module(self.USERS_MODULE)
            self.dashboard_page.select_chart_view_name(self.NON_LOCAL_USERS_QUERY_NAME)
            self.dashboard_page.select_chart_wizard_field(self.IS_ADMIN_OPTION_NAME)

        with self._edit_and_assert_chart(card, ['3'], self.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.select_chart_view_name(self.AD_BAD_CONFIG_QUERY_NAME)

        with self._edit_and_assert_chart(card, ['6'], self.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.select_chart_wizard_field(self.IS_LOCAL_OPTION_NAME)

        with self._edit_and_assert_chart(card, ['88', '13'], self.PIE_CHART_TYPE):
            self.dashboard_page.select_chart_view_name(self.NON_LOCAL_USERS_QUERY_NAME)
            self.dashboard_page.select_chart_wizard_field(self.IS_ADMIN_OPTION_NAME)
            self.dashboard_page.change_chart_type(self.PIE_CHART_TYPE)

    def _test_summary_chart_edit(self, card):
        with self._edit_and_assert_chart(card, ['15'], self.SUMMARY_CHART_TYPE):
            self.dashboard_page.select_chart_wizard_module(self.USERS_MODULE)
            self.dashboard_page.select_chart_wizard_field(self.USER_NAME_OPTION_NAME)
            self.dashboard_page.select_chart_summary_function(self.COUNT_OPTION_NAME)

        with self._edit_and_assert_chart(card, ['515'], self.SUMMARY_CHART_TYPE):
            self.dashboard_page.select_chart_summary_function(self.AVERAGE_OPTION_NAME)
            self.dashboard_page.select_chart_wizard_module(self.DEVICES_MODULE)
            self.dashboard_page.select_chart_wizard_adapter(AD_ADAPTER_NAME)
            self.dashboard_page.select_chart_wizard_field(self.AD_PRIMARY_GROUP_ID_OPTION_NAME)

    def _test_timeline_chart_edit(self, card):
        with self._edit_and_assert_chart(card, self.TEST_TIMELINE_SVG_CSS, self.TIMELINE_CHART_TYPE):
            self.dashboard_page.select_chart_view_name(WINDOWS_QUERY_NAME)

        with self._edit_and_assert_chart(card, self.TEST_TIMELINE_SVG_CSS, self.TIMELINE_CHART_TYPE):
            self.dashboard_page.toggle_comparison_intersection_switch()
            self.dashboard_page.select_chart_result_range_date()
            self.dashboard_page.select_chart_wizard_datepicker(1, datetime.datetime.now() + datetime.timedelta(-30))
            self.dashboard_page.close_datepicker()
            self.dashboard_page.select_chart_wizard_datepicker(2, datetime.datetime.now())
            self.dashboard_page.close_datepicker()
            views_list = self.dashboard_page.get_views_list()
            self.dashboard_page.select_chart_wizard_module(self.DEVICES_MODULE, views_list[1])
            self.dashboard_page.select_chart_view_name(MANAGED_DEVICES_QUERY_NAME, views_list[1])

        with self._edit_and_assert_chart(card, self.TEST_TIMELINE_SVG_CSS, self.TIMELINE_CHART_TYPE):
            views_list = self.dashboard_page.get_views_list()
            self.dashboard_page.select_chart_view_name(WINDOWS_QUERY_NAME, views_list[0])
            self.dashboard_page.select_chart_wizard_module(self.USERS_MODULE, views_list[1])
            self.dashboard_page.select_chart_view_name(self.NON_LOCAL_USERS_QUERY_NAME, views_list[1])

    def test_dashboard_segmentation_multiple_filters(self):
        # test for feature : https://axonius.atlassian.net/browse/AX-5662
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.open_new_card_wizard()
        self.dashboard_page.select_chart_metric('Field Segmentation')
        self.dashboard_page.fill_text_field_by_element_id(self.dashboard_page.CHART_TITLE_ID, self.TEST_EDIT_CARD_TITLE)
        assert self.dashboard_page.is_chart_segment_include_empty_enabled()
        self.dashboard_page.select_chart_wizard_module(self.DEVICES_MODULE)
        self.dashboard_page.select_chart_wizard_field(self.dashboard_page.FIELD_NETWORK_INTERFACES_IPS)
        assert not self.dashboard_page.is_card_save_button_disabled()
        assert self.dashboard_page.is_add_chart_segment_filter_button_disabled()
        self.dashboard_page.fill_chart_segment_filter(self.NETWORK_IPS_OPTION_NAME, '', 1)
        assert self.dashboard_page.is_card_save_button_disabled()
        self.dashboard_page.fill_chart_segment_filter(self.NETWORK_IPS_OPTION_NAME, '10', 1)
        assert not self.dashboard_page.is_chart_segment_include_empty_enabled()
        self.dashboard_page.remove_chart_segment_filter(1)
        assert self.dashboard_page.is_chart_segment_include_empty_enabled()
        self.fill_chart_segment_filter_and_add_filter(self.NETWORK_IPS_OPTION_NAME, '10.0', 1)
        self.fill_chart_segment_filter_and_add_filter(self.NETWORK_IPS_OPTION_NAME, '0.2.', 2)
        self.fill_chart_segment_filter_and_add_filter(self.NETWORK_MAC_OPTION_NAME, '06:3a', 3, True)
        self.dashboard_page.fill_chart_segment_filter(self.NETWORK_MAC_OPTION_NAME, '06:3a', 3)
        self.dashboard_page.click_card_save()
        card = self.dashboard_page.find_dashboard_card(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_histogram_lines_data(card, ['1', '1', '1'])

    def fill_chart_segment_filter_and_add_filter(self, filter_name, filter_value, filter_position, do_remove=False):
        self.dashboard_page.fill_chart_segment_filter(filter_name, filter_value, filter_position)
        self.dashboard_page.add_chart_segment_filter_row()
        if do_remove:
            self.dashboard_page.remove_chart_segment_filter(filter_position)
