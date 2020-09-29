from test_credentials.json_file_credentials import (DEVICE_FIRST_HOSTNAME, DEVICE_FIRST_NAME,
                                                    DEVICE_SECOND_NAME,
                                                    DEVICE_THIRD_IP)
from ui_tests.tests.query.query_test_base import QueryTestBase
from ui_tests.tests.ui_consts import JSON_ADAPTER_NAME


class TestQueryENT(QueryTestBase):

    def test_asset_entity_expressions(self):
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
        self.adapters_page.restore_json_client()
