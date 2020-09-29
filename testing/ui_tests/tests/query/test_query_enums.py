from axonius.consts.gui_consts import ADAPTER_CONNECTIONS_FIELD
from test_credentials.test_cisco_credentials import cisco_json_file_mock_credentials
from test_credentials.test_cylance_credentials import cylance_json_file_mock_credentials
from ui_tests.tests.query.query_test_base import QueryTestBase
from ui_tests.tests.ui_consts import JSON_ADAPTER_FILTER, COMP_EQUALS, JSON_ADAPTER_NAME


class TestQueryEnums(QueryTestBase):

    def _test_query_enum(self, field, value, comp_op, field_type, expected_query, subfield=None):
        self.devices_page.change_query_params(field, value, comp_op, field_type, subfield)
        assert self.devices_page.is_query_error()
        self.devices_page.wait_for_table_to_be_responsive()
        current_query = self.devices_page.find_query_search_input().get_attribute('value')
        assert current_query == expected_query

    def test_query_enum_basic(self):
        self.prepare_to_query()
        self._test_query_enum(ADAPTER_CONNECTIONS_FIELD, JSON_ADAPTER_NAME, COMP_EQUALS, 'string',
                              f'({JSON_ADAPTER_FILTER})')
        self.devices_page.clear_query_wizard()
        self._test_query_enum(self.devices_page.FIELD_OS_BITNESS, '64', COMP_EQUALS, 'integer',
                              '(specific_data.data.os.bitness == 64)')

    def test_query_enum_cisco(self):
        self.adapters_page.add_server(cisco_json_file_mock_credentials, JSON_ADAPTER_NAME)
        self.adapters_page.wait_for_server_green(position=2)
        self.prepare_to_query()
        self._test_query_enum('Port Access: Port Mode', 'singleHost', COMP_EQUALS, 'string',
                              '(specific_data.data.port_access.port_mode == "singleHost")')
        self.devices_page.clear_query_wizard()
        self._test_query_enum('Port Access', 'singleHost', COMP_EQUALS, 'string',
                              '(specific_data.data.port_access == match([(port_mode == "singleHost")]))',
                              subfield='Port Mode')
        self.devices_page.click_search()
        self.adapters_page.restore_json_client()

    def test_query_enum_cylance(self):
        self.adapters_page.add_server(cylance_json_file_mock_credentials, JSON_ADAPTER_NAME)
        self.adapters_page.wait_for_server_green(position=2)
        self.prepare_to_query()
        self._test_query_enum('Agent Versions', 'Cylance Agent', COMP_EQUALS, 'string',
                              '(specific_data.data.agent_versions == match([(adapter_name == "Cylance Agent")]))',
                              subfield='Name')
        self.devices_page.clear_query_wizard()
        self._test_query_enum('Agent Versions: Name', 'Cylance Agent', COMP_EQUALS, 'string',
                              '(specific_data.data.agent_versions.adapter_name == "Cylance Agent")')
        self.devices_page.click_search()
        self.adapters_page.restore_json_client()
