import pytest

from ui_tests.tests.ui_test_base import TestBase


class TestDashboard(TestBase):
    UNCOVERED_QUERY = '(not(specific_data.adapter_properties == "Manager")) and ' \
                      '(not(specific_data.adapter_properties == "Agent"))'
    COVERED_QUERY = 'specific_data.adapter_properties in [\'Manager\',\'Agent\']'
    SUMMARY_CARD_QUERY = 'specific_data.data.hostname == exists(true)'
    OS_WINDOWS_QUERY = 'specific_data.data.os.type == "Windows"'
    LAST_SEEN_7_DAY_QUERY = 'specific_data.data.last_seen < date("NOW - 7d")'
    INTERSECTION_QUERY = f'({OS_WINDOWS_QUERY}) and ({LAST_SEEN_7_DAY_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY = f'({OS_WINDOWS_QUERY}) and not ({LAST_SEEN_7_DAY_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY = f'not (({OS_WINDOWS_QUERY}) or ({LAST_SEEN_7_DAY_QUERY}))'
    NO_OS_QUERY = 'specific_data.data.os.type == exists(false)'
    SEGMENTATION_PIE_CARD_QUERY = 'specific_data.data.total_number_of_cores == exists(false)'

    @pytest.mark.skip('TBD')
    def test_system_empty_state(self):
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_show_me_how_button()
        assert self.dashboard_page.find_see_all_message()
        self.dashboard_page.assert_congratulations_message_found()

    def test_dashboard_sanity(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()

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
        self.dashboard_page.click_uncovered_pie_slice()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.UNCOVERED_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.click_covered_pie_slice()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.COVERED_QUERY

    def test_dashboard_intersection_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_intersection_card('Devices', 'Windows Operating System',
                                                  'Devices Not Seen In Last 7 Days', 'test intersection')
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.click_intersection_pie_slice()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.INTERSECTION_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.click_symmetric_difference_first_query_pie_slice()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.click_symmetric_difference_base_query_pie_slice()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.remove_intersection_card()

    def test_dashboard_summary_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count', 'test summary')
        self.dashboard_page.wait_for_spinner_to_end()
        summary_chart = self.dashboard_page.get_summary_card()
        result_count = int(summary_chart.text)
        summary_chart.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == result_count
        assert self.devices_page.find_search_value() == self.SUMMARY_CARD_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_summary_card()

    def test_dashboard_segmentation_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        # 'network interfaces' is not one of the options, it suppose to return false
        assert not self.dashboard_page.add_segmentation_card('Devices', 'network interfaces', 'test segmentation')
        self.dashboard_page.add_segmentation_card('Devices', 'OS: Type', 'test segmentation histogram')
        self.dashboard_page.wait_for_spinner_to_end()
        shc_card = self.dashboard_page.get_segmentation_histogram_card()
        shc_chart = self.dashboard_page.get_histogram_chart_from_card(shc_card)
        line = self.dashboard_page.get_histogram_line_from_histogram(shc_chart, 1)
        first_result_count = int(line.text)
        line.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == first_result_count
        assert self.devices_page.find_search_value() == self.OS_WINDOWS_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        shc_card = self.dashboard_page.get_segmentation_histogram_card()
        shc_chart = self.dashboard_page.get_histogram_chart_from_card(shc_card)
        line = self.dashboard_page.get_histogram_line_from_histogram(shc_chart, 2)
        second_result_count = int(line.text)
        line.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == second_result_count
        assert self.devices_page.find_search_value() == self.NO_OS_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.add_segmentation_card('Devices', 'Total Cores', 'test segmentation pie', 'pie')
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.click_segmentation_pie_card()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.SEGMENTATION_PIE_CARD_QUERY
        assert self.devices_page.count_entities() == 22
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_segmentation_histogram_card()
        self.dashboard_page.remove_segmentation_pie_card()

    def test_dashboard_search(self):
        string_to_search = 'be'
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.fill_query_value(string_to_search)
        self.dashboard_page.enter_search()
        self.dashboard_page.wait_for_table_to_load()
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
        self.devices_page.wait_for_table_to_load()
        devices_page_tables_count = self.devices_page.get_all_tables_counters()[0]
        assert devices_page_tables_count == dashboard_devices_table_count
        assert self.devices_page.find_search_value().count(f'regex("{string_to_search}", "i")') == 7
        assert any(host_name in s for s in self.devices_page.get_all_table_rows()[0])
        self.devices_page.page_back()
        self.dashboard_page.open_view_users()
        self.users_page.wait_for_table_to_load()
        users_tables_count = self.users_page.get_all_tables_counters()[0]
        assert users_tables_count == dashboard_users_table_count
        assert self.users_page.find_search_value().count(f'regex("{string_to_search}", "i")') == 6
        assert any(user_name in s for s in self.users_page.get_all_table_rows()[0])
