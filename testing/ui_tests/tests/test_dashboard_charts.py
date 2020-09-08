from ui_tests.tests.test_dashboard_chart_base import TestDashboardChartBase
from ui_tests.tests.ui_consts import (HOSTNAME_DC_QUERY,
                                      HOSTNAME_DC_QUERY_NAME,
                                      IPS_192_168_QUERY,
                                      IPS_192_168_QUERY_NAME,
                                      OS_TYPE_OPTION_NAME, WINDOWS_QUERY_NAME)


class TestDashboardCharts(TestDashboardChartBase):
    INTERSECTION_QUERY = f'({IPS_192_168_QUERY}) and ({HOSTNAME_DC_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY = f'({IPS_192_168_QUERY}) and not ({HOSTNAME_DC_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY = f'not (({IPS_192_168_QUERY}) or ({HOSTNAME_DC_QUERY}))'
    OSX_OPERATING_SYSTEM_FILTER = 'specific_data.data.os.type == "OS X"'
    OSX_OPERATING_SYSTEM_NAME = 'OS X Operating System'
    TEST_EMPTY_TITLE = 'test empty'

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

        def _test_comparison_save_disabled(module_query_list):
            self.dashboard_page.prepare_comparison_card(module_query_list,
                                                        title=self.TEST_EMPTY_TITLE, chart_type='pie')
            assert self.dashboard_page.is_chart_save_disabled()
            self.dashboard_page.click_card_cancel()

        valid_queries = [{'module': 'Devices', 'query': self.OSX_OPERATING_SYSTEM_NAME}] * 2
        _test_comparison_save_disabled(valid_queries + [{'module': '', 'query': ''}])
        _test_comparison_save_disabled(valid_queries + [{'module': 'Devices', 'query': ''}])

        self.dashboard_page.add_comparison_card([{'module': 'Devices', 'query': self.OSX_OPERATING_SYSTEM_NAME},
                                                 {'module': 'Devices', 'query': self.OSX_OPERATING_SYSTEM_NAME}],
                                                title=self.TEST_EMPTY_TITLE,
                                                chart_type='pie')

        assert self.dashboard_page.find_no_data_label()
        self.dashboard_page.remove_card(self.TEST_EMPTY_TITLE)

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
