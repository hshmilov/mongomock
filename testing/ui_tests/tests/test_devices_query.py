import random
import math
from datetime import datetime
from uuid import uuid4
from dateutil.relativedelta import relativedelta
import pytest
from pytest import raises
from selenium.common.exceptions import NoSuchElementException
from axonius.consts.gui_consts import ADAPTER_CONNECTIONS_FIELD
from axonius.utils.hash import get_preferred_quick_adapter_id
from axonius.utils.wait import wait_until
from json_file_adapter.service import DEVICES_DATA, FILE_NAME
from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.pages.adapters_page import CONNECTION_LABEL, CONNECTION_LABEL_UPDATED
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (AWS_ADAPTER,
                                      AWS_ADAPTER_NAME,
                                      AD_ADAPTER_NAME,
                                      JSON_ADAPTER_NAME,
                                      WINDOWS_QUERY_NAME,
                                      STRESSTEST_SCANNER_ADAPTER,
                                      STRESSTEST_ADAPTER, LINUX_QUERY_NAME, TANIUM_SQ_ADAPTER,
                                      TANIUM_ASSET_ADAPTER, TANIUM_DISCOVERY_ADAPTER)
from services.plugins.general_info_service import GeneralInfoService
from services.adapters.cisco_service import CiscoService
from services.adapters.esx_service import EsxService
from services.adapters.cylance_service import CylanceService
from services.adapters.aws_service import AwsService
from services.adapters.tanium_asset_service import TaniumAssetService
from services.adapters.tanium_discover_service import TaniumDiscoverService
from services.adapters.tanium_sq_service import TaniumSqService
from services.adapters import stresstest_scanner_service, stresstest_service
from test_credentials.json_file_credentials import (DEVICE_FIRST_IP,
                                                    DEVICE_THIRD_IP,
                                                    DEVICE_MAC,
                                                    DEVICE_SUBNET,
                                                    DEVICE_FIRST_VLAN_TAGID,
                                                    DEVICE_SECOND_VLAN_NAME,
                                                    DEVICE_FIRST_HOSTNAME,
                                                    DEVICE_FIRST_NAME,
                                                    DEVICE_SECOND_NAME,
                                                    USERS_DATA)
from test_credentials.test_aws_credentials import client_details as aws_client_details
from test_credentials.test_tanium_asset_credentials import CLIENT_DETAILS as tanium_asset_details
from test_credentials.test_tanium_discover_credentials import CLIENT_DETAILS as tanium_discovery_details
from test_credentials.test_tanium_sq_credentials import CLIENT_DETAILS as tanium_sq_details
from devops.scripts.automate_dev import credentials_inputer


# pylint: disable=C0302
class TestDevicesQuery(TestBase):
    SEARCH_TEXT_WINDOWS = 'Windows'
    SEARCH_TEXT_CB_FIRST = 'CB First'
    SEARCH_TEXT_TESTDOMAIN = 'TestDomain'
    ERROR_TEXT_QUERY_BRACKET = 'Missing {direction} bracket'
    CUSTOM_QUERY = 'Clear_query_test'
    CISCO_PLUGIN_NAME = 'cisco_adapter'
    CISCO_PRETTY_NAME = 'Cisco'
    ESX_PLUGIN_NAME = 'esx_adapter'
    ESX_PRETTY_NAME = 'VMware ESXi'
    CYCLANCE_PLUGIN_NAME = 'cylance_adapter'
    CYCLANCE_PRETTY_NAME = 'CylancePROTECT'

    QUERY_WIZARD_DATE_PICKER_VALUE = '2019-01-02 02:13:24.485Z'

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

    def test_in_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        ips = self.devices_page.get_column_data_inline_with_remainder(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)

        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_IN)
        self.devices_page.fill_query_string_value(','.join(ips))
        self.devices_page.wait_for_table_to_be_responsive()

        self.devices_page.click_search()

        self.devices_page.select_page_size(50)

        new_ips = self.devices_page.get_column_data_inline_with_remainder(
            self.devices_page.FIELD_NETWORK_INTERFACES_IPS)

        assert len([ip for ip in new_ips if ip.strip() == '']) == 0

        ips_set = set(ips)
        new_ips_set = set(new_ips)

        assert ips_set.issubset(new_ips_set)

        for ips in self.devices_page.get_column_cells_data_inline_with_remainder(
                self.devices_page.FIELD_NETWORK_INTERFACES_IPS):
            if isinstance(ips, list):
                assert len(ips_set.intersection(set(ips))) > 0
            else:
                assert ips in ips_set

    def test_in_adapters_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.select_page_size(50)

        all_adapters = set(self.devices_page.get_column_data_inline_with_remainder(ADAPTER_CONNECTIONS_FIELD))
        adapters = random.sample(all_adapters, math.ceil(len(all_adapters) / 2))

        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(ADAPTER_CONNECTIONS_FIELD)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_IN)
        self.devices_page.fill_query_string_value(','.join(adapters))
        self.devices_page.wait_for_table_to_be_responsive()

        self.devices_page.click_search()

        self.devices_page.select_page_size(50)

        new_adapters = set(self.devices_page.get_column_data_inline_with_remainder(ADAPTER_CONNECTIONS_FIELD))

        assert len([adapter for adapter in new_adapters if adapter.strip() == '']) == 0

        assert set(adapters).issubset(new_adapters)

        for adapters_values in self.devices_page.get_column_cells_data_inline_with_remainder(ADAPTER_CONNECTIONS_FIELD):
            if isinstance(adapters_values, list):
                assert len(set(adapters_values).intersection(set(adapters))) > 0
            else:
                assert adapters_values in adapters

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

    def _test_comp_op_change(self):
        """
        Testing that change of the comparison function resets the value, since its type may be different to previous
        """
        self.devices_page.select_query_field(ADAPTER_CONNECTIONS_FIELD)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE)
        self.devices_page.fill_query_value('2')
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS)
        assert not self.devices_page.get_query_value()

    def _test_adapters_filter_change_icon(self):
        """
        Testing the change in the field type icon - when using the adapters filter the icon changes to a special icon
        """
        assert not self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME)
        assert self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.clear_query_wizard()
        expressions = self.devices_page.find_expressions()
        self.devices_page.select_context_obj(expressions[0])
        assert not self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME)
        assert self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.select_context_all(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[0])
        assert self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.clear_query_wizard()

    def _test_and_expression(self):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) <= results_count
        self.devices_page.clear_query_wizard()

    def check_all_columns_exist(self, columns_list):
        assert all(column in self.devices_page.get_columns_header_text() for column in columns_list)

    def check_no_columns_exist(self, columns_list):
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
        self.check_no_columns_exist(columns_list)
        self.edit_columns(columns_list)
        self.check_all_columns_exist(columns_list)
        self._create_query()
        self.devices_page.wait_for_table_to_be_responsive()
        self.check_all_columns_exist(columns_list)
        self.devices_page.save_query_as(self.CUSTOM_QUERY)
        assert self.devices_page.find_query_title_text() == self.CUSTOM_QUERY
        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()
        select = self.driver.find_element_by_css_selector(self.devices_page.QUERY_FIELD_VALUE)
        assert select.text == self.devices_page.CHART_QUERY_FIELD_DEFAULT
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_be_responsive()
        self.check_all_columns_exist(columns_list)
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
        self.devices_page.close_datepicker()
        self.devices_page.wait_for_table_to_be_responsive()
        query_filter = self.devices_page.find_search_value()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == results_count
        assert self.devices_page.find_search_value() == query_filter
        assert self.devices_page.is_query_error(self.devices_page.MSG_ERROR_QUERY_WIZARD)

    def test_host_name_and_adapter_filters_query(self):
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
        assert results_count == self.devices_page.count_entities()
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert results_count == self.devices_page.count_entities()

        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()

        non_ad_count = self.devices_page.count_entities()
        assert results_count > non_ad_count
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        non_json_count = self.devices_page.count_entities()
        assert results_count > non_json_count
        assert non_json_count > non_ad_count

        self.devices_page.click_search()

        host_name_query = 'test host name'
        self.devices_page.click_save_query()
        self.devices_page.fill_query_name(host_name_query)
        self.devices_page.click_save_query_save_button()

        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()
        self.devices_page.click_search()

        self.devices_page.execute_saved_query(host_name_query)

        self.devices_page.click_query_wizard()
        assert self.devices_page.is_filtered_adapter_icon_exists()

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

    def _test_last_seen_query(self, query_comp_days=EntitiesPage.QUERY_COMP_DAYS):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[0])
        self.devices_page.select_query_comp_op(query_comp_days, parent=expressions[0])
        self.devices_page.fill_query_value(365, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op(query_comp_days, parent=expressions[1])
        self.devices_page.fill_query_value(1, parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        if query_comp_days == EntitiesPage.QUERY_COMP_DAYS:
            assert len(self.devices_page.get_all_data()) < results_count
        else:
            assert len(self.devices_page.get_all_data()) == results_count
        self.devices_page.clear_query_wizard()

    def _test_last_seen_query_last_days(self):
        self._test_last_seen_query(EntitiesPage.QUERY_COMP_DAYS)

    def _test_last_seen_query_with_next_days(self):
        self._test_last_seen_query(EntitiesPage.QUERY_COMP_NEXT_DAYS)

    def _test_last_seen_query_with_filter_adapters(self):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, parent=expressions[0])
        self.devices_page.fill_query_value(365, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[1])
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, parent=expressions[1])
        self.devices_page.fill_query_value(1, parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.find_search_value().count(self.devices_page.NAME_ADAPTERS_AD) == 1
        assert len(self.devices_page.get_all_data()) < results_count

        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 0
        assert self.devices_page.find_search_value().count(self.devices_page.NAME_ADAPTERS_AD) == 1
        assert self.devices_page.find_search_value().count(self.devices_page.NAME_ADAPTERS_JSON) == 1

        self.devices_page.clear_query_wizard()

    def _test_asset_name_query_with_filter_adapters(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.toggle_not(expressions[0])
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_ASSET_NAME, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) > 1
        assert self.devices_page.find_search_value().count(self.devices_page.NAME_ADAPTERS_AD) == 1

        self.devices_page.clear_query_wizard()

    def _test_query_brackets(self):
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.toggle_left_bracket(expressions[0])
        assert self.devices_page.is_query_error(self.ERROR_TEXT_QUERY_BRACKET.format(direction='right'))
        self.devices_page.toggle_right_bracket(expressions[1])
        assert self.devices_page.is_query_error()
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op(EntitiesPage.QUERY_COMP_DAYS, parent=expressions[2])
        self.devices_page.fill_query_value(30, parent=expressions[2])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.remove_query_expression(expressions[0])
        assert self.devices_page.is_query_error(self.ERROR_TEXT_QUERY_BRACKET.format(direction='left'))
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.toggle_right_bracket(expressions[0])
        assert self.devices_page.is_query_error()
        self.devices_page.clear_query_wizard()

    def _test_remove_query_expressions(self):
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SUBNET, parent=expressions[0])
        self.devices_page.fill_query_string_value('192.168.0.0/16', parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op('exists', parent=expressions[2])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data())
        current_filter = self.devices_page.find_search_value()
        self.devices_page.remove_query_expression(expressions[2])
        assert current_filter != self.devices_page.find_search_value()
        current_filter = self.devices_page.find_search_value()
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data())
        self.devices_page.remove_query_expression(expressions[0])
        assert current_filter != self.devices_page.find_search_value()
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def _test_remove_query_expression_does_not_reset_values(self):
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, parent=expressions[0])
        self.devices_page.fill_query_string_value('test', parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op(self.users_page.QUERY_COMP_DAYS, parent=expressions[1])
        self.devices_page.fill_query_value('1', parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR, parent=expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_ASSET_NAME, parent=expressions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, parent=expressions[2])
        self.devices_page.fill_query_string_value('test_device', parent=expressions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.remove_query_expression(expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        assert self.devices_page.get_query_value(parent=expressions[0]) == '1'
        assert self.devices_page.get_query_value(parent=expressions[1], input_type_string=True) == 'test_device'
        self.devices_page.clear_query_wizard()

    def _test_not_expression(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, parent=expressions[0])
        self.devices_page.fill_query_string_value('test', parent=expressions[0])
        self.devices_page.toggle_not(expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_field(self.devices_page.FIELD_SAVED_QUERY, parent=expressions[1])
        self.devices_page.select_query_value(WINDOWS_QUERY_NAME, parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert not len(self.devices_page.get_all_data())
        self.devices_page.toggle_not(expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_ASSET_NAME, parent=expressions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.toggle_not(expressions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert not len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def _test_complex_obj(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1

        # Prepare OBJ query with 2 nested conditions
        self.devices_page.select_context_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        self.devices_page.add_query_child_condition(expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 2

        # DEVICE_MAC and DEVICE_FIRST_IP are on same Network Interface, so Device will return
        self.devices_page.select_query_field(self.devices_page.FIELD_IPS, conditions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[0])
        self.devices_page.fill_query_string_value(DEVICE_FIRST_IP, conditions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_MAC, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, conditions[1])
        self.devices_page.fill_query_string_value(DEVICE_MAC, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 1

        # DEVICE_THIRD_IP and SUBNETS are not on same Network Interface, so Device will not return
        self.devices_page.fill_query_string_value(DEVICE_THIRD_IP, conditions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_SUBNETS, conditions[1])
        self.devices_page.fill_query_string_value(DEVICE_SUBNET, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 0

        # However, this IP and VLAN will return the device, when not using the OBJ feature
        self.devices_page.clear_query_wizard()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, expressions[0])
        self.devices_page.fill_query_string_value(DEVICE_THIRD_IP, expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_SUBNETS, expressions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, expressions[1])
        self.devices_page.fill_query_string_value(DEVICE_SUBNET, expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.clear_query_wizard()

        self._test_complex_obj_subnets()
        self._test_complex_obj_vlans()
        self._test_complex_obj_dates()

    def _test_complex_obj_subnets(self):
        # Network Interfaces -> Subnets exists should return results
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_context_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_SUBNETS, conditions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, conditions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def _test_complex_obj_vlans(self):
        # DEVICE_FIRST_TAGID and DEVICE_SECOND_VLAN_NAME are on same Network Interface and different Vlan, so:
        # Network Interfaces -> Vlans: Vlan Name and Vlans: Tag ID - returns result, however:
        # Network Interfaces: Vlans -> Vlan Name and Tag ID - does not
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_context_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        self.devices_page.add_query_child_condition()
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_VLANS_VLAN_NAME, conditions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[0])
        self.devices_page.fill_query_string_value(DEVICE_SECOND_VLAN_NAME, conditions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_VLANS_TAG_ID, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[1])
        self.devices_page.fill_query_value(DEVICE_FIRST_VLAN_TAGID, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data())
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_VLANS, expressions[0])
        self.devices_page.add_query_child_condition()
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_VLAN_NAME, conditions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[0])
        self.devices_page.fill_query_string_value(DEVICE_SECOND_VLAN_NAME, conditions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_TAG_ID, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[1])
        self.devices_page.fill_query_value(DEVICE_FIRST_VLAN_TAGID, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert not len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def _test_complex_obj_dates(self):
        self.devices_page.close_dropdown()
        with GeneralInfoService().contextmanager(take_ownership=True):
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()
            # Wait for WMI info
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(self.devices_page.AD_WMI_ADAPTER_FILTER)
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_be_responsive()

            wait_until(self.devices_page.get_all_data, total_timeout=60 * 25)
            # Refresh to have the Users field available (not automatically fetched)
            self.devices_page.refresh()
            self.devices_page.wait_for_table_to_be_responsive()

            # Start building complex query
            self.devices_page.click_query_wizard()
            self.devices_page.add_query_expression()
            expressions = self.devices_page.find_expressions()
            assert len(expressions) == 2
            self.devices_page.select_context_obj(expressions[0])
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS, expressions[0])
            conditions = self.devices_page.find_conditions(expressions[0])
            assert len(conditions) == 1
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS_LAST_USE, conditions[0])
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, conditions[0])
            self.devices_page.fill_query_value(2, conditions[0])
            self.devices_page.wait_for_table_to_be_responsive()

            assert len(self.devices_page.get_all_data())
            self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR)
            self.devices_page.select_context_obj(expressions[1])
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS, expressions[1])
            conditions = self.devices_page.find_conditions(expressions[1])
            assert len(conditions) == 1
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS_LAST_USE, conditions[0])
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, conditions[0])
            self.devices_page.fill_query_value(5, conditions[0])
            self.devices_page.wait_for_table_to_be_responsive()

            assert len(self.devices_page.get_all_data())
            self.devices_page.clear_query_wizard()

    def _test_adapters_size(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(ADAPTER_CONNECTIONS_FIELD)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE)
        self.devices_page.fill_query_value('1')
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 20
        self.devices_page.fill_query_value('2')
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 0
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE_BELOW)
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 20
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE_ABOVE)
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 0
        self.devices_page.fill_query_value('1')
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 0
        self.devices_page.fill_query_value('0')
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 20
        self.devices_page.clear_query_wizard()

    def _assert_query(self, expected_query):
        current_query = self.devices_page.find_query_search_input().get_attribute('value')
        assert current_query == expected_query

    def _perform_query_scenario(self, field, value, comp_op, field_type, expected_query, subfield=None, obj=False):
        self.devices_page.change_query_params(field, value, comp_op, field_type, subfield, obj)
        assert self.devices_page.is_query_error()
        self.devices_page.wait_for_table_to_be_responsive()
        self._assert_query(expected_query)

    def _test_enum_expressions(self):
        combo_configs = [
            # enum of type string
            {'field': ADAPTER_CONNECTIONS_FIELD,
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': 'Cisco',
             'field_type': 'string',
             'expected_query': '(adapters == "cisco_adapter")'},
            # enum of type string
            {'field': 'Port Access: Port Mode',
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': 'singleHost',
             'field_type': 'string',
             'expected_query': '(specific_data.data.port_access.port_mode == "singleHost")'},
            # enum of type string - displayed as Object (field and subfield)
            {'field': 'Port Access',
             'subfield': 'Port Mode',
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': 'singleHost',
             'field_type': 'string',
             'obj': True,
             'expected_query': '(specific_data.data.port_access == match([(port_mode == "singleHost")]))'},
            # enum of type string - displayed flat
            {'field': 'Agent Versions: Name',
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': 'Cylance Agent',
             'field_type': 'string',
             'expected_query': '(specific_data.data.agent_versions.adapter_name == "Cylance Agent")'},
            # enum of type string - displayed as Object (field and subfield)
            {'field': 'Agent Versions',
             'subfield': 'Name',
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': 'Cylance Agent',
             'field_type': 'string',
             'obj': True,
             'expected_query':
                 '(specific_data.data.agent_versions == match([(adapter_name == "Cylance Agent")]))'},
            # enum of type integer
            {'field': self.devices_page.FIELD_OS_BITNESS,
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': '64',
             'field_type': 'integer',
             'expected_query': '(specific_data.data.os.bitness == 64)'}
        ]
        with CiscoService().contextmanager(take_ownership=True), \
                EsxService().contextmanager(take_ownership=True),\
                CylanceService().contextmanager(take_ownership=True):
            credentials_inputer.main()
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            for conf in combo_configs:
                self.devices_page.click_query_wizard()
                self.devices_page.clear_query_wizard()
                self._perform_query_scenario(**conf)
                self.devices_page.click_search()
            self.devices_page.click_query_wizard()
            self.devices_page.clear_query_wizard()
            for conf in combo_configs:
                try:
                    self.driver.find_element_by_css_selector('.expression-context.selected')
                    self.devices_page.select_context_all(self.devices_page.find_expressions()[0])
                except NoSuchElementException:
                    # Nothing to do
                    pass
                self._perform_query_scenario(**conf)
            self.devices_page.click_search()
        self.adapters_page.clean_adapter_servers(self.CISCO_PRETTY_NAME)
        self.wait_for_adapter_down(self.CISCO_PLUGIN_NAME)
        self.adapters_page.clean_adapter_servers(self.ESX_PRETTY_NAME)
        self.wait_for_adapter_down(self.ESX_PLUGIN_NAME)
        self.adapters_page.clean_adapter_servers(self.CYCLANCE_PRETTY_NAME)
        self.wait_for_adapter_down(self.CYCLANCE_PLUGIN_NAME)

        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()

    def _test_asset_entity_expressions(self):
        self.devices_page.click_search()
        self.adapters_page.add_json_extra_client()
        self.base_page.run_discovery()

        # DEVICE_FIRST_HOSTNAME and DEVICE_SECOND_NAME on single Adapter Device - expected to find one
        self.devices_page.build_asset_entity_query(JSON_ADAPTER_NAME,
                                                   self.devices_page.FIELD_HOSTNAME_TITLE,
                                                   DEVICE_FIRST_HOSTNAME,
                                                   self.devices_page.FIELD_ASSET_NAME,
                                                   DEVICE_SECOND_NAME)
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 1
        children = self.devices_page.get_asset_entity_children_first()
        # DEVICE_THIRD_IP and DEVICE_SECOND_NAME on single Adapter Device - expected to find none
        self.devices_page.change_asset_entity_query(children[0],
                                                    self.devices_page.FIELD_NETWORK_INTERFACES_IPS,
                                                    DEVICE_THIRD_IP)
        self.devices_page.wait_for_table_to_be_responsive()
        assert not self.devices_page.get_all_data()
        # DEVICE_THIRD_IP and DEVICE_FIRST_NAME on single Adapter Device - expected to find none
        self.devices_page.change_asset_entity_query(children[1],
                                                    value_string=DEVICE_FIRST_NAME)
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 1

        self.devices_page.click_search()
        self.adapters_page.remove_json_extra_client()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()

    @pytest.mark.skip('AX-6585')
    def test_query_wizard_combos(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self._test_adapters_filter_change_icon()
        self._test_complex_obj()
        self._test_comp_op_change()
        self._test_and_expression()
        self._test_last_seen_query_last_days()
        self._test_last_seen_query_with_next_days()
        self._test_last_seen_query_with_filter_adapters()
        self._test_asset_name_query_with_filter_adapters()
        self._test_query_brackets()
        self._test_remove_query_expressions()
        self._test_remove_query_expression_does_not_reset_values()
        self._test_not_expression()
        self._test_adapters_size()
        self._test_enum_expressions()
        self._test_asset_entity_expressions()

    @pytest.mark.skip('AX-6079')
    def test_saved_query_field(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_LINUX, LINUX_QUERY_NAME)
        self.devices_page.click_query_wizard()

        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_SAVED_QUERY, parent=expressions[0])
        self.devices_page.select_query_value(WINDOWS_QUERY_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        for os_type in self.devices_page.get_column_data_slicer(self.devices_page.FIELD_OS_TYPE):
            assert os_type == self.devices_page.VALUE_OS_WINDOWS

        self.devices_page.select_query_value(LINUX_QUERY_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert not len(self.devices_page.get_all_data())

    def test_empty_fields_arent_there(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1

        self.devices_page.select_query_adapter(self.devices_page.VALUE_ADAPTERS_GENERAL, parent=expressions[0])
        fields = list(self.devices_page.get_all_fields_in_field_selection())
        # swap_cached is only returned by chef, not by AD or JSON
        assert 'Total Swap GB' not in fields
        assert 'Host Name' in fields

        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        fields = list(self.devices_page.get_all_fields_in_field_selection())
        assert 'Last Contact' in fields
        assert 'Cloud ID' not in fields
        assert 'Last Seen' not in fields
        assert 'AD Use DES Key Only' not in fields

        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        fields = list(self.devices_page.get_all_fields_in_field_selection())
        assert 'AD Use DES Key Only' in fields

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
        wait_until(lambda: '> 1000' in self.devices_page.get_raw_count_entities())
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

    def test_change_field_with_different_value_schema(self):
        with AwsService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[0][0])
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            expressions = self.devices_page.find_expressions()
            self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
            self.devices_page.select_query_comp_op('equals', parent=expressions[0])
            self.devices_page.fill_query_string_value('w', parent=expressions[0])
            self.devices_page.wait_for_table_to_be_responsive()
            query_filter = self.devices_page.find_search_value()
            results_count = len(self.devices_page.get_all_data())
            self.devices_page.select_query_field(self.devices_page.FIELD_FIREWALL_RULES_FROM_PORT,
                                                 parent=expressions[0])
            self.devices_page.wait_for_table_to_be_responsive()
            assert len(self.devices_page.get_all_data()) == results_count
            assert self.devices_page.find_search_value() == query_filter
            assert self.devices_page.is_query_error(self.devices_page.MSG_ERROR_QUERY_WIZARD)
            self.devices_page.click_search()

        self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME, delete_associated_entities=True)
        self.wait_for_adapter_down(AWS_ADAPTER)

    def test_in_enum_query(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
            with stress.contextmanager(take_ownership=True), \
                    stress_scanner.contextmanager(take_ownership=True):
                device_dict = {'device_count': 10, 'name': 'blah'}
                stress.add_client(device_dict)
                stress_scanner.add_client(device_dict)

                self.base_page.run_discovery()
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                self.devices_page.wait_for_table_to_be_responsive()

                self.devices_page.select_page_size(50)

                all_os_types = set(self.devices_page.
                                   get_column_data_inline_with_remainder(self.devices_page.FIELD_OS_TYPE))

                os_types = random.sample(all_os_types, math.ceil(len(all_os_types) / 2))

                self.devices_page.click_query_wizard()
                self.devices_page.select_query_field(self.devices_page.FIELD_OS_TYPE)
                self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_IN)
                self.devices_page.fill_query_string_value(','.join(set(os_types)))
                self.devices_page.wait_for_table_to_be_responsive()

                self.devices_page.click_search()

                new_os_types = set(self.devices_page.get_column_data_inline_with_remainder(
                    self.devices_page.FIELD_OS_TYPE))

                assert len([os_type for os_type in new_os_types if os_type.strip() == '']) == 0

                assert set(os_types).issubset(new_os_types)

                for os_types_values in self.devices_page.get_column_cells_data_inline_with_remainder(
                        self.devices_page.FIELD_OS_TYPE):
                    if isinstance(os_types_values, list):
                        assert len(set(os_types_values).intersection(set(os_types))) > 0
                    else:
                        assert os_types_values in os_types

        finally:
            self.wait_for_adapter_down(STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(STRESSTEST_SCANNER_ADAPTER)

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

    # pylint: disable=R0915
    def test_connection_label_query(self):
        """
        USE CASES :  add new AWS client with connection label
        test operator equal,exists,in
                      check negative with in
        update client connection label and check with eqal
        delete client connection label and check with in no match

        """

        with AwsService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            aws_client_with_label = aws_client_details[0][0].copy()
            aws_client_with_label.update({'connectionLabel': CONNECTION_LABEL})
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_with_label)
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            # check equal
            self.adapters_page.select_query_filter(attribute=self.devices_page.FIELD_ADAPTER_CONNECTION_LABEL,
                                                   operator='equals',
                                                   value=CONNECTION_LABEL)
            results_count = len(self.devices_page.get_all_data())
            assert results_count != 0
            # check exists
            self.adapters_page.select_query_filter(attribute=self.devices_page.FIELD_ADAPTER_CONNECTION_LABEL,
                                                   operator='exists',
                                                   clear_filter=True)
            results_count = len(self.devices_page.get_all_data())
            assert results_count != 0
            # check in negative value
            self.adapters_page.select_query_filter(attribute=self.devices_page.FIELD_ADAPTER_CONNECTION_LABEL,
                                                   operator='in',
                                                   value='NOT_EXISTS')
            results_count = len(self.devices_page.get_all_data())
            assert results_count == 0
            # chec in positve value
            self.adapters_page.select_query_filter(attribute=self.devices_page.FIELD_ADAPTER_CONNECTION_LABEL,
                                                   operator='in',
                                                   value=CONNECTION_LABEL)
            results_count = len(self.devices_page.get_all_data())
            assert results_count != 0
            # update adapter client connection label
            self.adapters_page.edit_server_conn_label(AWS_ADAPTER_NAME, CONNECTION_LABEL_UPDATED)
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            self.devices_page.wait_for_table_to_load()
            self.adapters_page.select_query_filter(attribute=self.devices_page.FIELD_ADAPTER_CONNECTION_LABEL,
                                                   operator='equals',
                                                   value=CONNECTION_LABEL_UPDATED,
                                                   clear_filter=True)
            results_count = len(self.devices_page.get_all_data())
            assert results_count != 0
            # delete adapter client connection label
            self.adapters_page.edit_server_conn_label(AWS_ADAPTER_NAME, '')
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            self.adapters_page.select_query_filter(attribute=self.devices_page.FIELD_ADAPTER_CONNECTION_LABEL,
                                                   operator='exists',
                                                   clear_filter=True)
            results_count = len(self.devices_page.get_all_data())
            assert results_count == 0

    def test_last_seen_next_days(self):

        def chabchab_in_result():
            self.devices_page.wait_for_table_to_load()
            return 'ChabChab' in self.devices_page.get_column_data_inline(
                self.devices_page.FIELD_ASSET_NAME)

        def json_query_filter_last_seen_next_days(days_value=0):
            self.devices_page.select_query_with_adapter(attribute=self.devices_page.FIELD_LAST_SEEN,
                                                        operator=self.devices_page.QUERY_COMP_NEXT_DAYS,
                                                        value=days_value)
            self.devices_page.wait_for_table_to_be_responsive()

        future_date = (datetime.utcnow() + relativedelta(years=+10)).strftime('%Y-%m-%d %H:%M:%SZ')
        client_details = {
            FILE_NAME: 'test_last_seen_next_days',
            DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, '''
               {
                   "devices" : [{
                       "id": "ChabChab",
                       "name": "ChabChab",
                       "hostname": "ChabChab",
                       "last_seen": "''' + future_date + '''",
                       "network_interfaces": [{
                           "mac": "06:3A:9B:D7:D7:CC",
                           "ips": ["172.21.12.12"]
                       }]
                   }],
                   "fields" : ["id", "network_interfaces", "name", "hostname", "last_seen"],
                   "additional_schema" : [],
                   "raw_fields" : []
                       }
               '''),
            USERS_DATA: FileForCredentialsMock(USERS_DATA, '''
                    {
                        "users" : [],
                         "fields" : [],
                         "additional_schema" : [],
                         "raw_fields" : []                      
                    }
                    ''')
        }

        self.adapters_page.add_server(client_details, adapter_name=JSON_ADAPTER_NAME)
        self.adapters_page.wait_for_data_collection_toaster_start()
        self.adapters_page.wait_for_data_collection_toaster_absent()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        json_query_filter_last_seen_next_days(1)
        assert chabchab_in_result() is False
        json_query_filter_last_seen_next_days(100)
        assert chabchab_in_result() is False
        json_query_filter_last_seen_next_days(10000)
        assert chabchab_in_result()

    def test_connection_label_query_with_same_client_id(self):
        """
            verify connection label when adapter client have same client_id ( like tanium adapters )
            use case : same label on multiple adapters then remove label from one adapter and compare device count
            is lower on label query.
        """

        def set_tanium_adapter_details(name, details):
            tanium_client_details = details.copy()
            tanium_client_details['connectionLabel'] = tanium_client_details.pop('connection_label')
            self.adapters_page.create_new_adapter_connection(name, tanium_client_details)

        with TaniumAssetService().contextmanager(take_ownership=True), \
                TaniumDiscoverService().contextmanager(take_ownership=True), \
                TaniumSqService().contextmanager(take_ownership=True):

            self.adapters_page.wait_for_adapter(TANIUM_SQ_ADAPTER)
            set_tanium_adapter_details(TANIUM_ASSET_ADAPTER, tanium_asset_details)
            set_tanium_adapter_details(TANIUM_DISCOVERY_ADAPTER, tanium_discovery_details)
            set_tanium_adapter_details(TANIUM_SQ_ADAPTER, tanium_sq_details)
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            all_tanium_count = self.devices_page.query_tanium_connection_label(tanium_asset_details)
            # remove label
            self.adapters_page.edit_server_conn_label(TANIUM_DISCOVERY_ADAPTER, 'UPDATE_LABEL')
            self.adapters_page.wait_for_data_collection_toaster_start()
            self.adapters_page.wait_for_data_collection_toaster_absent()
            tanium_discovery_details['connection_label'] = 'UPDATE_LABEL'
            tanium_discovery_count = self.devices_page.query_tanium_connection_label(tanium_discovery_details)
            # verify we have less devices now
            self.devices_page.click_search()
            updated_tanium_count = self.devices_page.query_tanium_connection_label(tanium_asset_details)
            assert all_tanium_count - tanium_discovery_count == updated_tanium_count
