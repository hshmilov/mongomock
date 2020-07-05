from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import DEVICES_SEEN_NEGATIVE_VALUE_QUERY
from ui_tests.tests.test_enforcement_config import JSON_NAME
from test_credentials.test_cisco_credentials import cisco_json_file_mock_credentials


class TestQueryWizard(TestBase):

    def test_query_wizard_negative_values(self):

        self.adapters_page.add_json_server(cisco_json_file_mock_credentials)

        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.add_query_last_seen_negative_value(JSON_NAME,
                                                             self.devices_page.FIELD_LAST_SEEN,
                                                             self.devices_page.QUERY_COMP_NEXT_DAYS,
                                                             -1)
        current_query = self.devices_page.find_search_value()
        assert DEVICES_SEEN_NEGATIVE_VALUE_QUERY == current_query
        assert self.devices_page.count_entities() == 1

        self.adapters_page.remove_json_extra_server(cisco_json_file_mock_credentials)
