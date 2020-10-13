import time
import pytest
from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG
from axonius.entities import EntityType
from axonius.utils import datetime
from services.adapters import stresstest_service
from services.axon_service import TimeoutException
from ui_tests.tests.ui_consts import (WINDOWS_QUERY_NAME, HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME,
                                      IPS_192_168_QUERY, IPS_192_168_QUERY_NAME, DEVICES_MODULE,
                                      MANAGED_DEVICES_QUERY_NAME, OS_SERVICE_PACK_OPTION_NAME, IS_ADMIN_OPTION_NAME,
                                      IS_LOCAL_OPTION_NAME, USER_NAME_OPTION_NAME, AD_ADAPTER_NAME,
                                      AD_PRIMARY_GROUP_ID_OPTION_NAME, USERS_MODULE, COUNT_OPTION_NAME,
                                      AVERAGE_OPTION_NAME, OS_TYPE_OPTION_NAME, NETWORK_IPS_OPTION_NAME,
                                      NETWORK_MAC_OPTION_NAME, STRESSTEST_ADAPTER_NAME, ASSET_NAME_FIELD_NAME,
                                      STRESSTEST_ADAPTER, TAGS_FIELD_NAME, TAGS_OPTION_NAME)
from ui_tests.tests.ui_test_base import TestBase


class TestDashboardActions(TestBase):
    TEST_EDIT_CARD_TITLE = 'Testonius'
    NON_LOCAL_USERS_QUERY_NAME = 'Non-local users'
    AD_ADMINS_QUERY_NAME = 'AD enabled users in \'Administrators\' group'
    AD_BAD_CONFIG_QUERY_NAME = 'AD enabled users with bad configurations'
    AD_NO_PASSWORD_EXPIRATION_OPTION = 'AD Enabled Users Whose Password Does Not Expire'
    AD_CRITICAL_USERS_OPTION_NAME = 'AD Enabled Critical Users'

    def test_dashboard_chart_edit(self):

        # enable unlimited timeline range feature flag
        self.axonius_system.db.plugins.gui.configurable_configs.update_config(
            FEATURE_FLAGS_CONFIG,
            {'query_timeline_range': True},
            upsert=True
        )

        self.base_page.refresh()

        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.create_saved_query(HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME)
        self.devices_page.create_saved_query(IPS_192_168_QUERY, IPS_192_168_QUERY_NAME)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_intersection_card(module=DEVICES_MODULE,
                                                  first_query=WINDOWS_QUERY_NAME,
                                                  second_query=MANAGED_DEVICES_QUERY_NAME,
                                                  title=self.TEST_EDIT_CARD_TITLE)
        card = self.dashboard_page.find_dashboard_card(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_pie_slices_data(card, ['92'])
        self._test_intersection_chart_edit(self.TEST_EDIT_CARD_TITLE)
        card = self._change_card_to_comparison(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_pie_slices_data(card, ['77', '23'])
        self._test_comparison_chart_edit(self.TEST_EDIT_CARD_TITLE)
        card = self._change_card_to_segmentation(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_histogram_lines_data(card, ['2', '1'])
        self._test_segmentation_chart_edit(card)
        card = self._change_card_to_summary(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_summary_text_data(card, ['23'])
        self._test_summary_chart_edit(card)
        card = self._change_card_to_timeline(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_timeline_svg_exist(card)
        self._test_timeline_chart_edit(card)

    def _change_card_to_comparison(self, title):
        self.dashboard_page.edit_card(title)
        self.dashboard_page.select_chart_metric('Query Comparison')
        assert self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.change_chart_type(self.dashboard_page.PIE_CHART_TYPE)
        views_list = self.dashboard_page.get_views_list()
        self.dashboard_page.select_chart_wizard_module(DEVICES_MODULE, views_list[0])
        self.dashboard_page.select_chart_view_name(WINDOWS_QUERY_NAME, views_list[0])
        self.dashboard_page.select_chart_wizard_module(DEVICES_MODULE, views_list[1])
        self.dashboard_page.select_chart_view_name(HOSTNAME_DC_QUERY_NAME, views_list[1])
        self.dashboard_page.click_card_save()
        return self.dashboard_page.get_card(card_title=title)

    def _change_card_to_segmentation(self, title):
        self.dashboard_page.edit_card(title)
        self.dashboard_page.select_chart_metric('Field Segmentation')
        assert self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.change_chart_type(self.dashboard_page.HISTOGRAM_CHART_TYPE)
        self.dashboard_page.select_chart_wizard_module(DEVICES_MODULE)
        self.dashboard_page.select_chart_view_name(WINDOWS_QUERY_NAME)
        self.dashboard_page.select_chart_wizard_field(OS_SERVICE_PACK_OPTION_NAME)
        self.dashboard_page.click_card_save()
        return self.dashboard_page.get_card(card_title=title)

    def _change_card_to_summary(self, title):
        self.dashboard_page.edit_card(title)
        self.dashboard_page.select_chart_metric('Field Summary')
        assert self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.select_chart_wizard_module(DEVICES_MODULE)
        self.dashboard_page.select_chart_wizard_field(OS_TYPE_OPTION_NAME)
        self.dashboard_page.select_chart_summary_function(COUNT_OPTION_NAME)
        self.dashboard_page.click_card_save()
        return self.dashboard_page.get_card(card_title=title)

    def _change_card_to_timeline(self, title):
        self._create_history(EntityType.Devices)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.edit_card(title)
        self.dashboard_page.select_chart_metric('Query Timeline')
        assert self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.select_chart_wizard_module(DEVICES_MODULE)
        self.dashboard_page.select_chart_view_name(WINDOWS_QUERY_NAME)

        self.dashboard_page.select_chart_result_range_last()
        self.dashboard_page.click_card_save()
        return self.dashboard_page.get_card(card_title=title)

    def _test_intersection_chart_edit(self, title):
        with self.dashboard_page.edit_and_assert_chart(self.dashboard_page.get_card(title),
                                                       ['28', '68'], self.dashboard_page.PIE_CHART_TYPE):
            self.dashboard_page.select_intersection_chart_first_query(HOSTNAME_DC_QUERY_NAME)

        with self.dashboard_page.edit_and_assert_chart(self.dashboard_page.get_card(title),
                                                       ['8', '28', '64'], self.dashboard_page.PIE_CHART_TYPE):
            self.dashboard_page.select_intersection_chart_second_query(WINDOWS_QUERY_NAME)

        with self.dashboard_page.edit_and_assert_chart(self.dashboard_page.get_card(title),
                                                       ['61', '39'], self.dashboard_page.PIE_CHART_TYPE):
            self.dashboard_page.select_chart_wizard_module(USERS_MODULE)
            self.dashboard_page.select_intersection_chart_first_query(self.NON_LOCAL_USERS_QUERY_NAME)
            self.dashboard_page.click_add_view()
            self.dashboard_page.select_intersection_chart_second_query(self.AD_ADMINS_QUERY_NAME)

        with self.dashboard_page.edit_and_assert_chart(self.dashboard_page.get_card(title),
                                                       ['50', '50'], self.dashboard_page.PIE_CHART_TYPE):
            self.dashboard_page.select_intersection_chart_second_query(self.AD_BAD_CONFIG_QUERY_NAME)

        with self.dashboard_page.edit_and_assert_chart(self.dashboard_page.get_card(title),
                                                       ['28', '22', '17', '33'],
                                                       self.dashboard_page.PIE_CHART_TYPE):
            self.dashboard_page.select_intersection_chart_first_query(self.AD_ADMINS_QUERY_NAME)

    def _test_comparison_chart_edit(self, card_title):
        with self.dashboard_page.edit_and_assert_chart(self.dashboard_page.find_dashboard_card(title=card_title),
                                                       ['51', '49'], self.dashboard_page.PIE_CHART_TYPE):
            views_list = self.dashboard_page.get_views_list()
            self.dashboard_page.select_chart_view_name(MANAGED_DEVICES_QUERY_NAME, views_list[1])

        with self.dashboard_page.edit_and_assert_chart(self.dashboard_page.find_dashboard_card(title=card_title),
                                                       ['24', '23'], self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.change_chart_type(self.dashboard_page.HISTOGRAM_CHART_TYPE)

        with self.dashboard_page.edit_and_assert_chart(self.dashboard_page.find_dashboard_card(title=card_title),
                                                       ['23', '18'], self.dashboard_page.HISTOGRAM_CHART_TYPE):
            views_list = self.dashboard_page.get_views_list()
            self.dashboard_page.select_chart_wizard_module(USERS_MODULE, views_list[1])
            self.dashboard_page.select_chart_view_name(self.NON_LOCAL_USERS_QUERY_NAME, views_list[1])

    def _test_segmentation_chart_edit(self, card):
        with self.dashboard_page.edit_and_assert_chart(card, ['2'], self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.fill_chart_segment_filter(OS_SERVICE_PACK_OPTION_NAME, '1')

        with self.dashboard_page.edit_and_assert_chart(card, ['16', '3'], self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.select_chart_wizard_module(USERS_MODULE)
            self.dashboard_page.select_chart_view_name(self.NON_LOCAL_USERS_QUERY_NAME)
            self.dashboard_page.select_chart_wizard_field(IS_ADMIN_OPTION_NAME)

        with self.dashboard_page.edit_and_assert_chart(card, ['8', '1'], self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.select_chart_view_name(self.AD_BAD_CONFIG_QUERY_NAME)

        with self.dashboard_page.edit_and_assert_chart(card, ['9'], self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.select_chart_wizard_field(IS_LOCAL_OPTION_NAME)

        with self.dashboard_page.edit_and_assert_chart(card, ['84', '16'], self.dashboard_page.PIE_CHART_TYPE):
            self.dashboard_page.select_chart_view_name(self.NON_LOCAL_USERS_QUERY_NAME)
            self.dashboard_page.select_chart_wizard_field(IS_ADMIN_OPTION_NAME)
            self.dashboard_page.change_chart_type(self.dashboard_page.PIE_CHART_TYPE)

    def _test_summary_chart_edit(self, card):
        with self.dashboard_page.edit_and_assert_chart(card, ['18'], self.dashboard_page.SUMMARY_CHART_TYPE):
            self.dashboard_page.select_chart_wizard_module(USERS_MODULE)
            self.dashboard_page.select_chart_wizard_field(USER_NAME_OPTION_NAME)
            self.dashboard_page.select_chart_summary_function(COUNT_OPTION_NAME)

        with self.dashboard_page.edit_and_assert_chart(card, ['515'], self.dashboard_page.SUMMARY_CHART_TYPE):
            self.dashboard_page.select_chart_summary_function(AVERAGE_OPTION_NAME)
            self.dashboard_page.select_chart_wizard_module(DEVICES_MODULE)
            self.dashboard_page.select_chart_wizard_adapter(AD_ADAPTER_NAME)
            self.dashboard_page.select_chart_wizard_field(AD_PRIMARY_GROUP_ID_OPTION_NAME)

    def _test_timeline_chart_edit(self, card):
        with self.dashboard_page.edit_and_assert_chart(card, None, self.dashboard_page.TIMELINE_CHART_TYPE):
            self.dashboard_page.select_chart_view_name(WINDOWS_QUERY_NAME)

        with self.dashboard_page.edit_and_assert_chart(card, None, self.dashboard_page.TIMELINE_CHART_TYPE):
            self.dashboard_page.toggle_comparison_intersection_switch()
            self.dashboard_page.select_chart_result_range_date()
            self.dashboard_page.select_chart_wizard_range_picker(
                date_from=datetime.datetime.now() + datetime.timedelta(-25),
                date_to=datetime.datetime.now())
            views_list = self.dashboard_page.get_views_list()
            self.dashboard_page.select_chart_wizard_module(DEVICES_MODULE, views_list[1])
            self.dashboard_page.select_chart_view_name(MANAGED_DEVICES_QUERY_NAME, views_list[1])

        with self.dashboard_page.edit_and_assert_chart(card, None, self.dashboard_page.TIMELINE_CHART_TYPE):
            views_list = self.dashboard_page.get_views_list()
            self.dashboard_page.select_chart_view_name(WINDOWS_QUERY_NAME, views_list[0])
            self.dashboard_page.select_chart_wizard_module(USERS_MODULE, views_list[1])
            self.dashboard_page.select_chart_view_name(self.NON_LOCAL_USERS_QUERY_NAME, views_list[1])

    def test_dashboard_segmentation_multiple_filters(self):
        # test for feature : https://axonius.atlassian.net/browse/AX-5662
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.open_new_card_wizard()
        self.dashboard_page.select_chart_metric('Field Segmentation')
        self.dashboard_page.fill_text_field_by_element_id(self.dashboard_page.CHART_TITLE_ID,
                                                          self.TEST_EDIT_CARD_TITLE)
        assert self.dashboard_page.is_chart_segment_include_empty_enabled()
        self.dashboard_page.select_chart_wizard_module(DEVICES_MODULE)
        self.dashboard_page.select_chart_wizard_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        assert not self.dashboard_page.is_card_save_button_disabled()
        assert self.dashboard_page.is_add_chart_segment_filter_button_disabled()
        self.dashboard_page.fill_chart_segment_filter(NETWORK_IPS_OPTION_NAME, '', 1)
        assert self.dashboard_page.is_card_save_button_disabled()
        self.dashboard_page.fill_chart_segment_filter(NETWORK_IPS_OPTION_NAME, '10', 1)
        assert not self.dashboard_page.is_chart_segment_include_empty_enabled()
        self.dashboard_page.remove_chart_segment_filter(1)
        assert self.dashboard_page.is_chart_segment_include_empty_enabled()
        self.fill_chart_segment_filter_and_add_filter(NETWORK_IPS_OPTION_NAME, '10.0', 1)
        self.fill_chart_segment_filter_and_add_filter(NETWORK_IPS_OPTION_NAME, '0.2.', 2)
        self.fill_chart_segment_filter_and_add_filter(NETWORK_MAC_OPTION_NAME, '06:3a', 3, True)
        self.dashboard_page.fill_chart_segment_filter(NETWORK_MAC_OPTION_NAME, '06:3a', 3)
        self.dashboard_page.click_card_save()
        card = self.dashboard_page.find_dashboard_card(self.TEST_EDIT_CARD_TITLE)
        self.dashboard_page.assert_histogram_lines_data(card, ['1', '1', '1'])

    def fill_chart_segment_filter_and_add_filter(self, filter_name, filter_value, filter_position, do_remove=False):
        self.dashboard_page.fill_chart_segment_filter(filter_name, filter_value, filter_position)
        self.dashboard_page.add_chart_segment_filter_row()
        if do_remove:
            self.dashboard_page.remove_chart_segment_filter(filter_position)

    def assert_current_page_and_total_items_histogram_chart(self, card, assert_data):
        total = self.dashboard_page.get_paginator_total_num_of_items(card)

        page = self.dashboard_page.get_paginator_active_page(card)
        assert assert_data == [page, total]

    def fill_card_search(self, card, text):
        self.dashboard_page.fill_card_search_input(card, text)

    def test_segmentation_chart_search_in_histogram(self):
        stress = stresstest_service.StresstestService()
        with stress.contextmanager(take_ownership=True):
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(STRESSTEST_ADAPTER_NAME)
            device_dict = {'device_count': 600, 'name': 'testonius'}
            self.adapters_page.add_server(device_dict, STRESSTEST_ADAPTER_NAME)
            self.adapters_page.wait_for_server_green()
            self.dashboard_page.switch_to_page()
            self.base_page.run_discovery()
            self.dashboard_page.add_segmentation_card(module=DEVICES_MODULE,
                                                      field=ASSET_NAME_FIELD_NAME,
                                                      title=self.TEST_EDIT_CARD_TITLE)
            self.dashboard_page.wait_for_spinner_to_end()
            card = self.dashboard_page.find_dashboard_card(self.TEST_EDIT_CARD_TITLE)
            self.assert_current_page_and_total_items_histogram_chart(card, ['1', '625'])
            self.fill_card_search(card, '10')

            # check search worked
            self.assert_current_page_and_total_items_histogram_chart(card, ['1', '17'])
            self.fill_card_search(card, 'avigdor')

            self.assert_current_page_and_total_items_histogram_chart(card, ['1', '600'])
            for _ in range(12):
                self.dashboard_page.click_to_next_page(card)
            # check for total number wont change after fetch more data
            self.assert_current_page_and_total_items_histogram_chart(card, ['13', '600'])
            self.dashboard_page.clear_card_search(card=card)
            # check if get back to page one
            self.assert_current_page_and_total_items_histogram_chart(card, ['1', '625'])
            self.fill_card_search(card, '100')
            self.assert_current_page_and_total_items_histogram_chart(card, ['1', '1'])
            self.dashboard_page.edit_card(self.TEST_EDIT_CARD_TITLE)
            self.dashboard_page.click_card_save()
            # wait for animation to finish
            time.sleep(1)
            # check if filter reset
            self.assert_current_page_and_total_items_histogram_chart(card, ['1', '1'])
            assert self.dashboard_page.get_card_search_input_text(card) == ''
            self.adapters_page.clean_adapter_servers(STRESSTEST_ADAPTER_NAME)
        self.wait_for_adapter_down(STRESSTEST_ADAPTER)

    def _add_tags_to_list_of_row_numbers(self, row_numbers, tags):
        """
        add tags to multiple entities
        :param row_numbers: list of integers representing the row numbers to tag, start at 1
        :param tags: list of tags to add to the entities
        :return:
        """
        for x in row_numbers:
            self.devices_page.click_row_checkbox(x)
        self.devices_page.add_new_tags(tags, len(row_numbers))
        assert self.devices_page.verify_no_entities_selected()

    def test_segmentation_chart_tags_filter(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        # add tags to devices
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self._add_tags_to_list_of_row_numbers([1, 3, 5, 7], ['filter_search_tag1'])
        self._add_tags_to_list_of_row_numbers([2, 3, 4, 6, 7], ['filter_tag2'])
        self._add_tags_to_list_of_row_numbers([3, 4, 5], ['filter_tag3'])
        self._add_tags_to_list_of_row_numbers([2, 3], ['search_tag4'])
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.add_segmentation_card(module=DEVICES_MODULE,
                                                  field=TAGS_FIELD_NAME,
                                                  title=self.TEST_EDIT_CARD_TITLE)
        card = self.dashboard_page.find_dashboard_card(self.TEST_EDIT_CARD_TITLE)
        with self.dashboard_page.edit_and_assert_chart(card, ['5', '4', '3', '2'],
                                                       self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.check_chart_segment_include_empty()
        with self.dashboard_page.edit_and_assert_chart(card, ['5', '4', '3'],
                                                       self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.fill_chart_segment_filter(TAGS_OPTION_NAME, 'filter', 1)
        with self.dashboard_page.edit_and_assert_chart(card, ['4', '2'],
                                                       self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.fill_chart_segment_filter(TAGS_OPTION_NAME, 'search', 1)
        histogram_chart = self.dashboard_page.get_histogram_chart_from_card(card)
        line = self.dashboard_page.get_histogram_line_from_histogram(histogram_chart, 1)
        line.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == 4
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.remove_card(self.TEST_EDIT_CARD_TITLE)

    def test_fetching_data_during_edit_chart(self):
        """
        Tests that during the edit of a dashboard chart, the loading indicator
        would display "Fetching data..." as long as data is being loaded

        - We will edit the chart two times, in each time checking that:
          - A) The "No data" is not appearing
          - B) The "Fetching data..." is appearing

        We do it twice to make sure it behaves consistently.
        """
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card(module='Devices',
                                                  field=OS_TYPE_OPTION_NAME,
                                                  title=self.TEST_EDIT_CARD_TITLE)

        for _ in range(2):
            self.dashboard_page.edit_card(self.TEST_EDIT_CARD_TITLE)
            self.dashboard_page.click_button('Save')
            with pytest.raises(TimeoutException):
                self.dashboard_page.wait_for_element_present_by_css(self.dashboard_page.NO_DATA_FOUND_SPINNER_CSS)
