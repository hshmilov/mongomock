from axonius.utils.wait import wait_until
from services.adapters.wmi_service import WmiService
from test_credentials.json_file_credentials import (DEVICE_FIRST_IP, DEVICE_THIRD_IP,
                                                    DEVICE_MAC, DEVICE_SUBNET, DEVICE_SECOND_VLAN_NAME,
                                                    DEVICE_FIRST_VLAN_TAGID)

from ui_tests.tests.query.query_test_base import QueryTestBase
from ui_tests.tests.ui_consts import COMP_EQUALS, COMP_CONTAINS, COMP_EXISTS, COMP_DAYS, LOGIC_OR, LOGIC_AND


class TestQueryOBJ(QueryTestBase):

    def test_query_obj_general(self):
        self.prepare_to_query()
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
        self.devices_page.select_query_comp_op(COMP_EQUALS, conditions[0])
        self.devices_page.fill_query_string_value(DEVICE_FIRST_IP, conditions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_MAC, conditions[1])
        self.devices_page.select_query_comp_op(COMP_CONTAINS, conditions[1])
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
        self.devices_page.select_query_comp_op(COMP_EQUALS, expressions[0])
        self.devices_page.fill_query_string_value(DEVICE_THIRD_IP, expressions[0])
        self.devices_page.select_query_logic_op(LOGIC_AND, expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_SUBNETS, expressions[1])
        self.devices_page.select_query_comp_op(COMP_CONTAINS, expressions[1])
        self.devices_page.fill_query_string_value(DEVICE_SUBNET, expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 1

    def test_query_obj_subnets(self):
        # Network Interfaces -> Subnets exists should return results
        self.prepare_to_query()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_context_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_SUBNETS, conditions[0])
        self.devices_page.select_query_comp_op(COMP_EXISTS, conditions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data())

    def test_query_obj_vlans(self):
        self.prepare_to_query()
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
        self.devices_page.select_query_comp_op(COMP_EQUALS, conditions[0])
        self.devices_page.fill_query_string_value(DEVICE_SECOND_VLAN_NAME, conditions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_VLANS_TAG_ID, conditions[1])
        self.devices_page.select_query_comp_op(COMP_EQUALS, conditions[1])
        self.devices_page.fill_query_value(DEVICE_FIRST_VLAN_TAGID, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data())
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_VLANS, expressions[0])
        self.devices_page.add_query_child_condition()
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_VLAN_NAME, conditions[0])
        self.devices_page.select_query_comp_op(COMP_EQUALS, conditions[0])
        self.devices_page.fill_query_string_value(DEVICE_SECOND_VLAN_NAME, conditions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_TAG_ID, conditions[1])
        self.devices_page.select_query_comp_op(COMP_EQUALS, conditions[1])
        self.devices_page.fill_query_value(DEVICE_FIRST_VLAN_TAGID, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert not len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def test_query_obj_dates(self):
        with WmiService().contextmanager(take_ownership=True):
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()
            # Wait for WMI info
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()
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
            self.devices_page.select_query_comp_op(COMP_DAYS, conditions[0])
            self.devices_page.fill_query_value(2, conditions[0])
            self.devices_page.wait_for_table_to_be_responsive()

            assert len(self.devices_page.get_all_data())
            self.devices_page.select_query_logic_op(LOGIC_OR)
            self.devices_page.select_context_obj(expressions[1])
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS, expressions[1])
            conditions = self.devices_page.find_conditions(expressions[1])
            assert len(conditions) == 1
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS_LAST_USE, conditions[0])
            self.devices_page.select_query_comp_op(COMP_DAYS, conditions[0])
            self.devices_page.fill_query_value(5, conditions[0])
            self.devices_page.wait_for_table_to_be_responsive()

            assert len(self.devices_page.get_all_data())
