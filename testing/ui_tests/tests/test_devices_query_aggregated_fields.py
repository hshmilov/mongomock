import datetime
import time
import pytest

from axonius.utils.wait import wait_until
from services.adapters.stresstest_service import StresstestService
from ui_tests.tests.ui_consts import STRESSTEST_ADAPTER_NAME
from ui_tests.tests.ui_test_base import TestBase

BASE_HOSTNAME_SEARCH_EQ = '(specific_data.data.hostname == "vm")'
BASE_LAST_SEEN_LESS = '(specific_data.data.last_seen < date("{}"))'

BASE_AGGR_HOSTNAME_SEARCH_REGEX = '(hostnames == regex("vm", "i"))'
BASE_HOSTNAME_SEARCH_REGEX_W_TOGGLE = '(specific_data.data.hostname == regex("vm", "i"))'
BASE_AGGR_HOSTNAME_SEARCH_EXISTS = '((hostnames == ({"$exists":true,"$ne":""})))'
BASE_HOSTNAME_SEARCH_EXISTS_W_TOGGLE = '((specific_data.data.hostname == ({"$exists":true,"$ne":""})))'

BASE_AGGR_LAST_SEEN_SEARCH_DAYS = '(last_seen >= date("NOW - 1d"))'
BASE_LAST_SEEN_SEARCH_DAYS_W_TOGGLE = '(specific_data.data.last_seen >= date("NOW - 1d"))'
BASE_LAST_SEEN_GREATER = '(last_seen > date("{}"))'
BASE_LAST_SEEN_GREATER_W_TOGGLE = '(specific_data.data.last_seen > date("{}"))'
# pylint: disable=W1401


class TestDevicesQueryAggregated(TestBase):

    def _test_comp_method(self, aggr_op, normal_op, expected_aggr_search, expected_aggr_search_w_toggle,
                          expected_normal_search, agg_value_fill_callback, normal_value_fill_callback):
        """
        Tests a comparison method changes the field name the search field.
        Also verifies that when we toggle outdated the field name returns to it's normal value instead of the
        aggregated one
        :param aggr_op: the aggregation comparison operand that will use the aggregation field
        :param normal_op: a normal comparison operand that won't use the aggregation field
        :param expected_aggr_search: expected search output when using the aggr_op
        :param expected_aggr_search_w_toggle: expected search output when using the aggr_op and toggle is on
        :param expected_normal_search: expected search output when using the comp_op
        :param agg_value_fill_callback: fill callback for value in query wizard for agg op
        :param normal_value_fill_callback: fill callback for value in query wizard for normal op
        :raise AssertionError if test fails
        """
        self.devices_page.select_query_comp_op(aggr_op)
        agg_value_fill_callback()
        search_value = self.devices_page.find_search_value()
        assert search_value == expected_aggr_search
        self.devices_page.select_query_comp_op(normal_op)
        normal_value_fill_callback()
        search_value = self.devices_page.find_search_value()
        assert search_value == expected_normal_search
        self.devices_page.select_query_comp_op(aggr_op)
        agg_value_fill_callback()
        search_value = self.devices_page.find_search_value()
        assert search_value == expected_aggr_search
        self.devices_page.click_wizard_outdated_toggle()
        search_value = self.devices_page.find_search_value()
        assert search_value == f'INCLUDE OUTDATED: {expected_aggr_search_w_toggle}'
        self.devices_page.click_wizard_outdated_toggle()
        search_value = self.devices_page.find_search_value()
        assert search_value == expected_aggr_search

    def _use_date_picker(self, value):
        self.devices_page.fill_query_wizard_date_picker(value)
        self.devices_page.close_datepicker()

    def _check_aggregator_log(self, modified_count=1):
        tester = self.axonius_system.aggregator.log_tester
        wait_until(lambda: tester.is_pattern_in_log(
            f'"message": "Took \d+.\d+ seconds, matched {modified_count}, modified {modified_count}"', 5))

    @pytest.mark.skip('AX-5956')
    def test_hostname_aggregated(self):
        """
        Tests using hostname (contains) X or hostname = X will result in the usage of the aggregate field hostnames
        """
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()

        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE)
        # Test equals comparison contains
        self._test_comp_method(
            self.devices_page.QUERY_COMP_CONTAINS,
            self.devices_page.QUERY_COMP_EQUALS,
            BASE_AGGR_HOSTNAME_SEARCH_REGEX,
            BASE_HOSTNAME_SEARCH_REGEX_W_TOGGLE,
            BASE_HOSTNAME_SEARCH_EQ,
            lambda: self.devices_page.fill_query_string_value('vm'),
            lambda: self.devices_page.fill_query_string_value('vm')

        )
        # Test exists comparison operation
        self._test_comp_method(
            self.devices_page.QUERY_COMP_EXISTS,
            self.devices_page.QUERY_COMP_EQUALS,
            BASE_AGGR_HOSTNAME_SEARCH_EXISTS,
            BASE_HOSTNAME_SEARCH_EXISTS_W_TOGGLE,
            BASE_HOSTNAME_SEARCH_EQ,
            lambda: None,
            lambda: self.devices_page.fill_query_string_value('vm'))

    @pytest.mark.skip('AX-5956')
    def test_last_seen_aggregated(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()

        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN)
        # Test days comparison contains
        self._test_comp_method(
            self.devices_page.QUERY_COMP_DAYS,
            self.devices_page.QUERY_COMP_LESS_THAN,
            BASE_AGGR_LAST_SEEN_SEARCH_DAYS,
            BASE_LAST_SEEN_SEARCH_DAYS_W_TOGGLE,
            BASE_LAST_SEEN_LESS.format(datetime.datetime.now().strftime('%Y-%m-%d')),
            lambda: self.devices_page.fill_query_value(1),
            lambda: self._use_date_picker(datetime.datetime.now()),
        )
        # Test greather than comparison operation
        self._test_comp_method(
            self.devices_page.QUERY_COMP_GREATER_THAN,
            self.devices_page.QUERY_COMP_LESS_THAN,
            BASE_LAST_SEEN_GREATER.format(datetime.datetime.now().strftime('%Y-%m-%d')),
            BASE_LAST_SEEN_GREATER_W_TOGGLE.format(datetime.datetime.now().strftime('%Y-%m-%d')),
            BASE_LAST_SEEN_LESS.format(datetime.datetime.now().strftime('%Y-%m-%d')),
            lambda: self._use_date_picker(datetime.datetime.now()),
            lambda: self._use_date_picker(datetime.datetime.now()))

    def test_add_custom_hostname_data(self):
        """
        Tests adding a hostname field in custom data should aggregate the field inside hostnames in the db
        """
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.click_custom_data_tab()
        self.devices_page.click_custom_data_edit()
        self.devices_page.click_custom_data_add_predefined()
        parent = self.devices_page.find_custom_fields_items()[-1]
        self.devices_page.select_custom_data_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=parent)
        self.devices_page.fill_custom_data_value('DeanSysman', parent=parent, input_type_string=True)
        self.devices_page.save_custom_data()
        self.devices_page.wait_for_spinner_to_end()
        # Aggregator should match 1 and modified 1 on this change
        self._check_aggregator_log()
        time.sleep(5)
        cursor = self.axonius_system.get_devices_db().find({'hostnames': {'$regex': '.*DeanSysman.*'}})
        d = cursor.next()
        assert 'DeanSysman' in d['hostnames']

        self.devices_page.click_custom_data_edit()
        parent = self.devices_page.find_custom_fields_items()[-1]
        self.devices_page.fill_custom_data_value('DeanSysman2', parent=parent, input_type_string=True)
        self.devices_page.save_custom_data()
        self.devices_page.wait_for_spinner_to_end()
        self._check_aggregator_log()
        # There is a small delay that can take up to five seconds until the data is modifieds
        time.sleep(5)
        cursor = self.axonius_system.get_devices_db().find({'hostnames': {'$regex': '.*DeanSysman2.*'}})
        d = cursor.next()
        assert 'DeanSysman2' in d['hostnames']

    def test_linking_devices(self):
        """
        Tests linking and unlinking devices saves the hostnames field correctly
        """
        clients_db = None
        try:
            with StresstestService().contextmanager(take_ownership=True) as service:
                clients_db = service.self_database['clients']
                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(STRESSTEST_ADAPTER_NAME)
                self.adapters_page.click_adapter(STRESSTEST_ADAPTER_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()

                for i in range(0, 3):
                    self.adapters_page.click_new_server()
                    self.adapters_page.fill_creds(**{
                        'device_count': 1,
                        'name': f'{i}'
                    })
                    self.adapters_page.click_save()
                    self.adapters_page.wait_for_spinner_to_end()
                    # let them adapters fill up
                    time.sleep(10)
                self.devices_page.switch_to_page()
                self.devices_page.wait_for_table_to_load()
                assert len(self.devices_page.get_all_data()) == 1
                for d in self.axonius_system.get_devices_db().find({}):
                    assert d['hostnames'] == 'vm-0.stress.axonius'
                self.devices_page.select_all_current_page_rows_checkbox()
                self.devices_page.open_unlink_dialog()
                wait_until(lambda: 'You are about to unlink 1 devices.' in self.devices_page.read_delete_dialog())
                self.devices_page.confirm_link()
                self._check_aggregator_log(3)

                assert len(self.devices_page.get_all_data()) == 3
                for d in self.axonius_system.get_devices_db().find({}):
                    assert d['hostnames'] == 'vm-0.stress.axonius'

                self.devices_page.select_all_current_page_rows_checkbox()
                self.devices_page.open_link_dialog()
                self.devices_page.confirm_link()
                self.devices_page.refresh()
                self.devices_page.wait_for_table_to_load()
                assert len(self.devices_page.get_all_data()) == 1
                self._check_aggregator_log(1)
        finally:
            if clients_db:
                clients_db.delete_many({})
