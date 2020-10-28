from datetime import datetime, timedelta
from axonius.entities import EntityType
from services.adapters import stresstest_service
from ui_tests.tests.test_dashboard_chart_base import TestDashboardChartBase
from ui_tests.tests.ui_consts import (OS_TYPE_OPTION_NAME, STRESSTEST_ADAPTER_NAME, TAGS_FIELD_NAME, DEVICES_MODULE,
                                      ASSET_NAME_FIELD_NAME)


class TestDashboardSegmentationChart(TestDashboardChartBase):

    TEST_SEGMENTATION_TITLE = 'test segmentation'
    SEGMENTATION_WITH_TIMELINE_CARD_TITLE = 'Segmentation & Timeline'
    TEST_TAGS_SEGMENTATION_TITLE = 'Test tags segmentation'
    TEST_TAG_WINDOWS = 'test_win_tag'
    TEST_TAG_GCP = 'test_gcp_tag'

    def _create_tags_by_search_term(self, tags_dict):
        expected_values = {}

        for tag_name, search_term in tags_dict.items():
            self.devices_page.search(search_term)
            self.devices_page.toggle_select_all_rows_checkbox()
            expected_values[tag_name] = self.devices_page.get_table_count()

            self.devices_page.open_actions_menu()
            self.devices_page.click_actions_tag_button()
            self.devices_page.fill_tags_input_text(tag_name)
            self.devices_page.click_create_new_tag_link_button()
            self.devices_page.click_tag_save_button()
            self.devices_page.wait_for_success_tagging_message(expected_values[tag_name])

        return expected_values

    def test_segmentation_pie_total_values(self):
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card('Devices', OS_TYPE_OPTION_NAME, self.TEST_SEGMENTATION_TITLE, 'pie')

        self.dashboard_page.wait_for_spinner_to_end()
        pie = self.dashboard_page.get_card(self.TEST_SEGMENTATION_TITLE)
        slices_total_items = self.dashboard_page.get_pie_chart_slices_total_value(pie)
        footer_total_items = self.dashboard_page.get_pie_chart_footer_total_value(pie)
        assert slices_total_items == footer_total_items
        self.dashboard_page.remove_card(self.TEST_SEGMENTATION_TITLE)

    def test_check_segmentation_csv(self):
        histogram_items_title = []
        chart = \
            self.dashboard_page.create_and_get_paginator_segmentation_card(
                run_discovery=True,
                module='Devices',
                field='Host Name',
                title=self.TEST_SEGMENTATION_TITLE,
                view_name='')
        histogram_card = chart.get('card')

        num_of_pages = self.dashboard_page.get_num_of_pages_paginator(histogram_card)

        histogram_card = self.dashboard_page.get_card(card_title=self.TEST_SEGMENTATION_TITLE)
        histograms_chart = self.dashboard_page.get_histogram_chart_from_card(card=histogram_card)
        histogram_items_title.append(self.dashboard_page.get_histogram_current_page_item_titles(histograms_chart))
        self.dashboard_page.click_to_next_page(histogram_card)
        self.dashboard_page.wait_for_card_spinner_to_end()

        # iterate incrementaly on all the pages (next)
        for page_number in range(1, num_of_pages):
            histogram_card = self.dashboard_page.get_card(card_title=self.TEST_SEGMENTATION_TITLE)
            histograms_chart = self.dashboard_page.get_histogram_chart_from_card(card=histogram_card)
            histogram_items_title.append(self.dashboard_page.get_histogram_current_page_item_titles(histograms_chart))

            if page_number == num_of_pages:
                break
            else:
                self.dashboard_page.click_to_next_page(histogram_card)
                self.dashboard_page.wait_for_card_spinner_to_end()

        # flatten list
        histogram_titles_list = [item for sublist in histogram_items_title for item in sublist]
        csv_data = self._download_and_get_csv(self.TEST_SEGMENTATION_TITLE)
        host_names_list = [x[0] for x in csv_data]
        # compare histograms_item_titles of pagination with data grabbed from devices table
        self.dashboard_page.assert_data_devices_fit_pagination_data(histogram_titles_list, host_names_list)
        self.dashboard_page.remove_card(self.TEST_SEGMENTATION_TITLE)

    def test_segmentation_tags(self):
        tags = {
            self.TEST_TAG_WINDOWS: 'WIN',
            self.TEST_TAG_GCP: 'gcp'
        }
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        expected_vals = self._create_tags_by_search_term(tags)

        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card(DEVICES_MODULE, TAGS_FIELD_NAME,
                                                  self.TEST_TAGS_SEGMENTATION_TITLE,
                                                  include_empty=False)
        self.dashboard_page.wait_for_spinner_to_end()
        data_dict = self.dashboard_page.get_histogram_chart_values(self.TEST_TAGS_SEGMENTATION_TITLE)

        for tag_name in expected_vals:
            assert int(data_dict[tag_name]) == expected_vals[tag_name]

    def test_timeline_button_disabled_when_date_exceed(self):
        with stresstest_service.StresstestService().contextmanager(take_ownership=True):
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(STRESSTEST_ADAPTER_NAME)
            self.adapters_page.add_server({'device_count': 600, 'name': 'testonius'}, STRESSTEST_ADAPTER_NAME)
            self.adapters_page.wait_for_server_green()
            self.base_page.run_discovery()
            self.dashboard_page.switch_to_page()
            assert self.dashboard_page.add_basic_segmentation_card(module=DEVICES_MODULE,
                                                                   field=ASSET_NAME_FIELD_NAME,
                                                                   title=self.SEGMENTATION_WITH_TIMELINE_CARD_TITLE,
                                                                   include_timeline=True)
            self.dashboard_page.wait_for_spinner_to_end()
            self._create_history(EntityType.Devices)
            self.dashboard_page.refresh()
            self.dashboard_page.switch_to_page()
            card = self.dashboard_page.find_dashboard_card(self.SEGMENTATION_WITH_TIMELINE_CARD_TITLE)
            self.dashboard_page.fill_card_search_date(card, (datetime.now() - timedelta(days=30)))
            assert self.dashboard_page.check_segmentation_card_timeline_disabled(card)
