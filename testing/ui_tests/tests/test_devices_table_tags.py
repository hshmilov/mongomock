from axonius.utils.wait import wait_until
from services.plugins.general_info_service import GeneralInfoService
from ui_tests.tests.test_entities_table import TestEntitiesTable
from ui_tests.tests.ui_consts import WINDOWS_QUERY_NAME


class TestDevicesTable(TestEntitiesTable):
    LABELS_TEXTBOX_TEXT = 'Connection Error'
    ALL_TAG_TEST = 'all tag test'
    LABEL_OS_SERVICE_PACK_ISSUE = 'OS_Service_Pack_issue'
    LABEL_A_MAJOR_ISSUE = 'A_MAJOR_ISSUE'
    LABEL_TAG_BUG = 'BUG'
    LABEL_CASE_ID = 'W-XX-12224-MM'

    def test_devices_action_add_and_remove_tag(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row_checkbox()
        self.devices_page.add_new_tags([self.LABELS_TEXTBOX_TEXT])
        assert self.LABELS_TEXTBOX_TEXT in self.devices_page.get_first_row_tags()
        self.devices_page.remove_first_tag()
        assert not self.devices_page.get_first_row_tags()

    def test_devices_action_remove_plugin_tag(self):
        with GeneralInfoService().contextmanager(take_ownership=True):
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            wait_until(lambda: any(self.devices_page.get_column_data_slicer(
                self.devices_page.FIELD_TAGS)), total_timeout=60 * 5)
            self.settings_page.switch_to_page()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_spinner_to_end()
            self.devices_page.click_sort_column(self.devices_page.FIELD_TAGS)
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_row_checkbox()
            tag_to_remove = self.devices_page.get_first_tag_text()
            self.devices_page.remove_tag(tag_to_remove)
            assert tag_to_remove not in self.devices_page.get_first_row_tags()

    def test_devices_action_add_tag_all_with_filter(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.execute_saved_query(WINDOWS_QUERY_NAME)
        self.devices_page.select_all_current_page_rows_checkbox()
        self.devices_page.click_select_all_entities()
        self.devices_page.add_new_tags([self.ALL_TAG_TEST], self.devices_page.get_table_count())
        assert self.ALL_TAG_TEST in self.devices_page.get_first_row_tags()
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.run_filter_query(self.devices_page.SPECIFIC_JSON_ADAPTER_FILTER)
        assert self.ALL_TAG_TEST not in self.devices_page.get_first_row_tags()

    def test_partial_tags(self):
        self._add_partial_tags()
        self._test_partial_tag_circularity()
        self._change_partial_tags_state()
        self._validate_tags()
        self._test_remove_all_tags()

    def _add_partial_tags(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        # Select the first row
        self.devices_page.click_row_checkbox(1)
        self.devices_page.add_new_tags([self.LABEL_A_MAJOR_ISSUE])
        # Unselect the first row
        self.devices_page.click_row_checkbox(1)
        # Select the second row
        self.devices_page.click_row_checkbox(2)
        self.devices_page.add_new_tags([self.LABEL_CASE_ID, self.LABEL_TAG_BUG])
        # Select the first row (now the first and second rows are selected
        self.devices_page.click_row_checkbox(1)
        self.devices_page.add_new_tags([self.LABEL_OS_SERVICE_PACK_ISSUE], 2)

    def _test_partial_tag_circularity(self):
        self.devices_page.open_tag_dialog()
        partial = self.devices_page.toggle_partial_tag(self.LABEL_TAG_BUG)
        assert self.devices_page.has_class(partial['tag_icon_ele'], self.devices_page.PartialIcon['CHECKED'])
        assert partial['tag_input_ele'].get_attribute('aria-checked') == self.devices_page.PartialState['CHECKED']
        partial = self.devices_page.toggle_partial_tag(self.LABEL_TAG_BUG)
        assert self.devices_page.has_class(partial['tag_icon_ele'], self.devices_page.PartialIcon['UNCHECKED'])
        assert partial['tag_input_ele'].get_attribute('aria-checked') == self.devices_page.PartialState['UNCHECKED']
        partial = self.devices_page.toggle_partial_tag(self.LABEL_TAG_BUG)
        assert self.devices_page.has_class(partial['tag_icon_ele'], self.devices_page.PartialIcon['PARTIAL'])
        assert partial['tag_input_ele'].get_attribute('aria-checked') == self.devices_page.PartialState['PARTIAL']
        self.devices_page.click_tag_save_button()

    def _change_partial_tags_state(self):
        tags_meta = [{'name': self.LABEL_A_MAJOR_ISSUE, 'state': self.devices_page.PartialState['UNCHECKED'],
                      'icon': self.devices_page.PartialIcon['UNCHECKED']},
                     {'name': self.LABEL_CASE_ID, 'state': self.devices_page.PartialState['CHECKED'],
                      'icon': self.devices_page.PartialIcon['CHECKED']}]
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        tags = self.devices_page.get_row_cell_text(row_index=1, cell_index=10)
        assert tags.split() == [self.LABEL_A_MAJOR_ISSUE, self.LABEL_OS_SERVICE_PACK_ISSUE]
        self.devices_page.click_row_checkbox(1)
        self.devices_page.click_row_checkbox(2)
        self.devices_page.open_tag_dialog()
        for tag in tags_meta:
            partial_tag_icon_ele = self.devices_page.set_partial_tag_to_state(tag)
            assert self.devices_page.has_class(partial_tag_icon_ele, tag['icon'])
        self.devices_page.click_tag_save_button()

    def _validate_tags(self):
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        # row 1
        self.devices_page.click_row_checkbox(1)
        new_tags_meta = [{'name': self.LABEL_A_MAJOR_ISSUE, 'state': self.devices_page.PartialState['UNCHECKED'],
                          'icon': self.devices_page.PartialIcon['UNCHECKED']},
                         {'name': self.LABEL_CASE_ID, 'state': self.devices_page.PartialState['CHECKED'],
                          'icon': self.devices_page.PartialIcon['CHECKED']},
                         {'name': self.LABEL_OS_SERVICE_PACK_ISSUE, 'state': self.devices_page.PartialState['CHECKED'],
                          'icon': self.devices_page.PartialIcon['CHECKED']},
                         {'name': self.LABEL_TAG_BUG, 'state': self.devices_page.PartialState['UNCHECKED'],
                          'icon': self.devices_page.PartialIcon['UNCHECKED']}]
        self._assert_validation_tags(new_tags_meta)
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        # row 2
        self.devices_page.click_row_checkbox(2)
        new_tags_meta = [{'name': self.LABEL_A_MAJOR_ISSUE, 'state': self.devices_page.PartialState['UNCHECKED'],
                          'icon': self.devices_page.PartialIcon['UNCHECKED']},
                         {'name': self.LABEL_CASE_ID, 'state': self.devices_page.PartialState['CHECKED'],
                          'icon': self.devices_page.PartialIcon['CHECKED']},
                         {'name': self.LABEL_OS_SERVICE_PACK_ISSUE, 'state': self.devices_page.PartialState['CHECKED'],
                          'icon': self.devices_page.PartialIcon['CHECKED']},
                         {'name': self.LABEL_TAG_BUG, 'state': self.devices_page.PartialState['CHECKED'],
                          'icon': self.devices_page.PartialIcon['CHECKED']}
                         ]
        self._assert_validation_tags(new_tags_meta)

    def _assert_validation_tags(self, tags):
        self.devices_page.open_tag_dialog()
        for tag in tags:
            partial_tag_icon_ele = self.driver.find_element_by_xpath(
                self.devices_page.TAG_PARTIAL_INPUT_ICON.format(tag_text=tag['name']))
            if tag['state'] == self.devices_page.PartialState['CHECKED']:
                assert self.devices_page.has_class(partial_tag_icon_ele, tag['icon'])
            elif tag['state'] == self.devices_page.PartialState['UNCHECKED']:
                assert self.devices_page.has_class(partial_tag_icon_ele, tag['icon'])
        self.devices_page.click_tag_save_button()

    def _test_remove_all_tags(self):
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.select_all_current_page_rows_checkbox()
        self.devices_page.click_select_all_entities()
        self.devices_page.remove_all_tags([self.LABEL_A_MAJOR_ISSUE, self.LABEL_CASE_ID,
                                           self.LABEL_OS_SERVICE_PACK_ISSUE, self.LABEL_TAG_BUG])
