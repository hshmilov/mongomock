import math
import random
from datetime import datetime
from uuid import uuid4

from pytest import raises

from axonius.utils.hash import get_preferred_quick_adapter_id
from axonius.utils.wait import wait_until
from test_credentials.json_file_credentials import (DEVICE_MAC,
                                                    DEVICE_THIRD_IP)
from ui_tests.tests.ui_consts import (AD_ADAPTER_NAME,
                                      JSON_ADAPTER_NAME)
from ui_tests.tests.ui_test_base import TestBase


# pylint: disable=C0302
class TestDevicesSimpleQuery(TestBase):
    SEARCH_TEXT_WINDOWS = 'Windows'
    SEARCH_TEXT_CB_FIRST = 'CB First'
    SEARCH_TEXT_TESTDOMAIN = 'TestDomain'
    CUSTOM_QUERY = 'Clear_query_test'
    QUERY_WIZARD_DATE_PICKER_VALUE = '02-01-2019 02:13:24.485Z'

    def test_bad_subnet(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SUBNET)
        self.devices_page.fill_query_string_value('1.1.1.1')
        self.devices_page.wait_for_element_present_by_text('Specify <address>/<CIDR> to filter IP by subnet')
        self.devices_page.click_search()

    def test_in_with_delimiter_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.click_row_checkbox()

        special_tag = 'a\\,b'

        self.devices_page.add_new_tags(['a\\,b'])

        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_TAGS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_IN)
        self.devices_page.fill_query_string_value(special_tag)
        self.devices_page.wait_for_table_to_be_responsive()

        self.devices_page.click_search()

        assert self.devices_page.count_entities() == 1

    def test_devices_query_wizard_default_operators(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME)
        assert self.devices_page.get_query_field() == self.devices_page.ID_FIELD
        assert self.devices_page.get_query_comp_op() == self.devices_page.QUERY_COMP_EXISTS

    def test_devices_query_wizard_list_field(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_USED_USERS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_STARTS)
        self.devices_page.fill_query_string_value('test')
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.count_entities() == 1
        self.devices_page.fill_query_string_value('test 3')
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.count_entities() == 0

    def _check_search_text_result(self, text):
        self.devices_page.enter_search()
        self.devices_page.wait_for_table_to_load()
        all_data = self.devices_page.get_all_data()
        assert len(all_data)
        assert any(text in x for x in all_data)

    def test_search_everywhere_exact_search_off(self):
        self.settings_page.set_exact_search(False)
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(self.SEARCH_TEXT_WINDOWS)
        self.devices_page.enter_search()
        self._check_search_text_result(self.SEARCH_TEXT_WINDOWS)
        # check contains works when exact search is off
        self.devices_page.fill_filter(self.SEARCH_TEXT_TESTDOMAIN)
        self.devices_page.open_search_list()
        self.devices_page.select_search_everywhere()
        self._check_search_text_result(self.SEARCH_TEXT_TESTDOMAIN)

        # contains won't work when exact search is on
        self.devices_page.fill_filter('Dom')
        self.devices_page.enter_search()
        self._check_search_text_result('Dom')

    def test_search_everywhere_exact_search_on(self):
        self.settings_page.set_exact_search(True)
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(self.SEARCH_TEXT_WINDOWS)
        self.devices_page.enter_search()
        self._check_search_text_result(self.SEARCH_TEXT_WINDOWS)
        self.devices_page.fill_filter(self.SEARCH_TEXT_CB_FIRST)
        self.devices_page.open_search_list()
        self.devices_page.select_search_everywhere()
        self._check_search_text_result(self.SEARCH_TEXT_CB_FIRST)
        self.devices_page.click_query_wizard()
        self._check_search_text_result(self.SEARCH_TEXT_CB_FIRST)
        self.devices_page.fill_filter(self.SEARCH_TEXT_CB_FIRST.lower())
        self.devices_page.enter_search()
        self._check_search_text_result(self.SEARCH_TEXT_CB_FIRST)

        # contains won't work when exact search is on
        self.devices_page.fill_filter('dom')
        self.devices_page.enter_search()
        with raises(AssertionError):
            self._check_search_text_result('dom')

    def _check_all_columns_exist(self, columns_list):
        assert all(column in self.devices_page.get_columns_header_text() for column in columns_list)

    def _check_no_columns_exist(self, columns_list):
        assert not any(column in self.devices_page.get_columns_header_text() for column in columns_list)

    def edit_columns(self, column_list):
        self.devices_page.edit_columns(add_col_names=column_list,
                                       adapter_title=self.devices_page.VALUE_ADAPTERS_GENERAL)

    def _create_query(self):
        self.devices_page.click_query_wizard()
        self.users_page.add_query_expression()
        self.users_page.add_query_expression()

        expressions = self.devices_page.find_expressions()
        self.devices_page.toggle_not(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_OS_MAJOR, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS)

        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_OS_BUILD, parent=expressions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[1])

        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_PART_OF_DOMAIN, parent=expressions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_TRUE, parent=expressions[2])
        self.devices_page.click_search()

    def test_clear_query_wizard(self):
        columns_list = [self.devices_page.FIELD_OS_MAJOR, self.devices_page.FIELD_OS_BUILD,
                        self.devices_page.FIELD_PART_OF_DOMAIN]
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self._check_no_columns_exist(columns_list)
        self.edit_columns(columns_list)
        self._check_all_columns_exist(columns_list)
        self._create_query()
        self.devices_page.wait_for_table_to_be_responsive()
        self._check_all_columns_exist(columns_list)
        self.devices_page.save_query_as(self.CUSTOM_QUERY)
        assert self.devices_page.find_query_title_text() == self.CUSTOM_QUERY
        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()
        select = self.driver.find_element_by_css_selector(self.devices_page.QUERY_FIELD_VALUE)
        assert select.text == self.devices_page.CHART_QUERY_FIELD_DEFAULT
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_be_responsive()
        self._check_all_columns_exist(columns_list)
        assert self.devices_page.find_query_title_text() == 'New Query'

    def test_change_comp_op_with_different_value_schema(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[0])
        self.devices_page.select_query_comp_op('>', parent=expressions[0])
        self.devices_page.fill_query_wizard_date_picker(self.QUERY_WIZARD_DATE_PICKER_VALUE, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        query_filter = self.devices_page.find_search_value()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == results_count
        assert self.devices_page.find_search_value() == query_filter
        assert self.devices_page.is_query_error(self.devices_page.MSG_ERROR_QUERY_WIZARD)

    def test_obj_network_and_adapter_filters_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_context_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, parent=expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_IPS, conditions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, conditions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = self.devices_page.count_entities()
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        assert results_count > self.devices_page.count_entities()

    def test_save_query(self):
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.toggle_left_bracket(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, expressions[0])
        self.devices_page.fill_query_string_value(DEVICE_THIRD_IP, expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_MAC, expressions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, expressions[1])
        self.devices_page.fill_query_string_value(DEVICE_MAC, expressions[1])
        self.devices_page.toggle_right_bracket(expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert not self.devices_page.is_query_save_as_disabled()
        self.devices_page.toggle_right_bracket(expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_save_as_disabled()
        self.devices_page.toggle_right_bracket(expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert not self.devices_page.is_query_save_as_disabled()

    def test_quick_count(self):
        """
        Tests that before calculating the whole count of the query, a quick >1000 is shown
        """
        devices_count = 100 * 1000  # 100k
        db = self.axonius_system.get_devices_db()

        def generate_fake_device(id_):
            data_id_ = f'yay-{id_}'
            return {
                'internal_axon_id': uuid4().hex,
                'accurate_for_datetime': datetime.now(),
                'adapters': [
                    {
                        'client_used': 'yes',
                        'plugin_type': 'Adapter',
                        'plugin_name': 'stresstest_adapter',
                        'plugin_unique_name': 'stresstest_adapter_0',
                        'type': 'entitydata',
                        'accurate_for_datetime': datetime.now(),
                        'quick_id': get_preferred_quick_adapter_id(data_id_, 'stresstest_adapter_0'),
                        'data': {
                            'random_text_for_love_and_prosperity': '19',
                            'id': data_id_,
                            'pretty_id': f'AX-{id_}'
                        }
                    }
                ],
                'tags': [],
                'adapter_list_length': 1
            }

        # inserting a lot of devices
        db.insert_many(generate_fake_device(x)
                       for x
                       in range(devices_count))

        # carefully chosen to be damn slow
        slow_query = ' and '.join(f'adapters_data.stresstest_adapter.random_text_for_love_and_prosperity != "{x}"'
                                  for x
                                  in range(10))

        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(slow_query)
        self.devices_page.enter_search()
        wait_until(lambda: 'Loading' in self.devices_page.get_raw_count_entities())
        assert self.devices_page.count_entities() == devices_count

    def test_adapters_filter_all_vs_clear_selection(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = self.devices_page.count_entities()
        self.devices_page.click_on_clear_all_filter_adapters(parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        query = self.devices_page.find_query_search_input()
        assert results_count == self.devices_page.count_entities()
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert results_count == self.devices_page.count_entities()
        assert query == self.devices_page.find_query_search_input()

    def test_exclude_entities_with_no_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()

        self._text_exclude_entities_on_current_data()

    def test_exclude_with_or_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op('exists', parent=expressions[2])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_be_responsive()
        self._text_exclude_entities_on_current_data()

    def test_exclude_clear_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.click_query_wizard()
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op('exists', parent=expressions[2])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_be_responsive()
        filtered_out_indices = self._text_exclude_entities_on_current_data()
        self.devices_page.click_query_wizard()
        self.devices_page.click_filter_out_clear()
        self.devices_page.wait_for_table_to_be_responsive()

        self.devices_page.count_selected_entities()
        for index in filtered_out_indices:
            assert self.devices_page.is_toggle_selected(self.devices_page.get_row_checkbox(index))

    def _text_exclude_entities_on_current_data(self):
        real_devices_count = self.devices_page.count_entities()
        devices_count = real_devices_count
        # limit the number of devices to sample to the first page
        devices_count = devices_count if devices_count <= 20 else 20
        indices = random.sample(range(1, devices_count), math.ceil(devices_count / 3))
        for index in indices:
            self.devices_page.click_row_checkbox(index)
        self.devices_page.open_filter_out_dialog()
        self.devices_page.confirm_filter_out()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == (real_devices_count - len(indices))
        return indices

    def test_saved_query_with_empty_expression(self):
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        expressions = self.devices_page.find_expressions()
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, expressions[0])
        self.devices_page.fill_query_string_value(DEVICE_THIRD_IP, expressions[0])
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_load()
        query = self.devices_page.find_search_value()
        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()

        self.devices_page.run_filter_query(query)
        self.devices_page.click_search()
        self.devices_page.save_query('test')

        self.devices_queries_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.wait_for_spinner_to_end()

        self.devices_queries_page.find_query_row_by_name('test').click()
        self.devices_queries_page.verify_no_query_defined()
