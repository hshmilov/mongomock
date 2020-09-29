from axonius.consts.gui_consts import ADAPTER_CONNECTIONS_FIELD
from test_credentials.test_aws_credentials_mock import aws_json_file_mock_devices
from ui_tests.tests.query.query_test_base import QueryTestBase
from ui_tests.tests.ui_consts import (COMP_CONTAINS, COMP_EQUALS, COMP_DAYS, COMP_SUBNET,
                                      LOGIC_OR,
                                      AD_ADAPTER_NAME, COMP_SIZE, JSON_ADAPTER_NAME, LOGIC_AND)


class TestQueryRemove(QueryTestBase):

    def test_remove_query_expressions(self):
        self.prepare_to_query()
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, parent=expressions[0])
        self.devices_page.select_query_comp_op(COMP_SUBNET, parent=expressions[0])
        self.devices_page.fill_query_string_value('192.168.0.0/16', parent=expressions[0])
        self.devices_page.select_query_logic_op(LOGIC_AND)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op('exists', parent=expressions[2])
        self.devices_page.select_query_logic_op(LOGIC_AND, parent=expressions[2])
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

    def test_remove_query_expression_values_remain(self):
        self.prepare_to_query()
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(COMP_CONTAINS, parent=expressions[0])
        self.devices_page.fill_query_string_value('test', parent=expressions[0])
        self.devices_page.select_query_logic_op(LOGIC_OR, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op(COMP_DAYS, parent=expressions[1])
        self.devices_page.fill_query_value('1', parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.select_query_logic_op(LOGIC_OR, parent=expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_ASSET_NAME, parent=expressions[2])
        self.devices_page.select_query_comp_op(COMP_EQUALS, parent=expressions[2])
        self.devices_page.fill_query_string_value('test_device', parent=expressions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.remove_query_expression(expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        assert self.devices_page.get_query_value(parent=expressions[0]) == '1'
        assert self.devices_page.get_query_value(parent=expressions[1], input_type_string=True) == 'test_device'

    def test_change_query_op_resets_value(self):
        self.prepare_to_query()
        self.devices_page.select_query_field(ADAPTER_CONNECTIONS_FIELD)
        self.devices_page.select_query_comp_op(COMP_SIZE)
        self.devices_page.fill_query_value('2')
        self.devices_page.select_query_comp_op(COMP_EQUALS)
        assert not self.devices_page.get_query_value()

    def test_change_field_with_different_value_schema(self):
        self.adapters_page.add_server(aws_json_file_mock_devices, JSON_ADAPTER_NAME)
        self.adapters_page.wait_for_server_green(position=2)

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
        self.devices_page.clear_query_wizard()
        self.devices_page.click_search()

        self.adapters_page.remove_server(ad_client=aws_json_file_mock_devices, adapter_name=JSON_ADAPTER_NAME,
                                         expected_left=1, delete_associated_entities=True,
                                         adapter_search_field=self.adapters_page.JSON_FILE_SERVER_SEARCH_FIELD)
