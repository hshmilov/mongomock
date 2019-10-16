import copy
import time

from selenium.common.exceptions import (ElementNotVisibleException,
                                        ElementNotInteractableException,
                                        NoSuchElementException)

from services.adapters.kaseya_service import KaseyaService
from testing.test_credentials.test_kaseya_credentials import client_details as kaseya_client_details
from ui_tests.tests.ui_consts import JSON_ADAPTER_NAME
from ui_tests.tests.ui_test_base import TestBase

KASEYA_VSA_ADAPTER_NAME = 'Kaseya VSA'
KASEYA_DOCKER_ADAPTER_NAME = 'kaseya_adapter'


class TestEntityCustomData(TestBase):
    CUSTOM_PREDEFINED_VALUE = 'A lovely name'
    CUSTOM_STRING_TYPE = 'String'
    CUSTOM_STRING_NAME = 'Building Name'
    CUSTOM_STRING_VALUE = 'Circular'
    CUSTOM_INT_TYPE = 'Integer'
    CUSTOM_INT_NAME = 'Floor Number'
    CUSTOM_INT_VALUE = '35'
    CUSTOM_FLOAT_TYPE = 'Float'
    CUSTOM_FLOAT_NAME = 'Usage Rate'
    CUSTOM_FLOAT_VALUE = '0.4'
    CUSTOM_BOOL_TYPE = 'Bool'
    CUSTOM_BOOL_NAME = 'Is Available'
    DUPLICATE_FIELD_ERROR = 'Custom Field Name is already in use by another field'
    CUSTOM_BULK_FIELD_VALUE = 'Best Bulk Value'

    @staticmethod
    def _test_init_state(entities_page):
        assert not entities_page.get_entity_id()
        assert entities_page.find_custom_data_edit()
        try:
            entities_page.click_advanced_view()
            assert False
        except (ElementNotVisibleException, ElementNotInteractableException):
            # Advanced not available on Custom Data tab
            pass
        try:
            entities_page.click_basic_view()
            assert False
        except NoSuchElementException:
            # Basic not available on Custom Data tab
            pass
        entities_page.click_tab(JSON_ADAPTER_NAME)
        entities_page.click_advanced_view()
        entities_page.click_custom_data_tab()
        assert not entities_page.find_element_by_text(entities_page.ADVANCED_VIEW_RAW_FIELD).is_displayed()

    def _test_first_data(self, entities_page, field_name):
        entities_page.click_custom_data_edit()
        entities_page.click_custom_data_add_predefined()
        assert entities_page.is_element_disabled(entities_page.find_custom_data_save())
        assert entities_page.is_input_error(entities_page.find_custom_data_predefined_field())
        entities_page.select_custom_data_field(field_name)
        assert entities_page.is_input_error(entities_page.find_custom_data_value())
        entities_page.fill_custom_data_value(self.CUSTOM_PREDEFINED_VALUE)
        entities_page.save_custom_data()
        entities_page.wait_for_spinner_to_end()
        assert entities_page.find_element_by_text(field_name) and entities_page.find_element_by_text(
            self.CUSTOM_PREDEFINED_VALUE)

    def _test_new_fields(self, entities_page):
        entities_page.click_custom_data_edit()
        self._create_new_field(entities_page, self.CUSTOM_STRING_TYPE, self.CUSTOM_STRING_NAME,
                               self.CUSTOM_STRING_VALUE, bad_name='!@#$%^&*()-\'/|.;,')
        self._create_new_field(entities_page, self.CUSTOM_INT_TYPE, self.CUSTOM_INT_NAME,
                               self.CUSTOM_INT_VALUE, bad_value='-a.')
        self._create_new_field(entities_page, self.CUSTOM_FLOAT_TYPE, self.CUSTOM_FLOAT_NAME, self.CUSTOM_FLOAT_VALUE)
        self._create_new_field(entities_page, self.CUSTOM_BOOL_TYPE, self.CUSTOM_BOOL_NAME)

        # Check all saved
        entities_page.save_custom_data()
        assert entities_page.find_element_by_text(self.CUSTOM_STRING_NAME) \
            and entities_page.find_element_by_text(self.CUSTOM_STRING_VALUE)
        assert entities_page.find_element_by_text(self.CUSTOM_INT_NAME) \
            and entities_page.find_element_by_text(self.CUSTOM_INT_VALUE)
        assert entities_page.find_element_by_text(self.CUSTOM_FLOAT_NAME) \
            and entities_page.find_element_by_text(self.CUSTOM_FLOAT_VALUE)
        assert entities_page.find_element_by_text(self.CUSTOM_BOOL_NAME)

    @staticmethod
    def _create_new_field(entities_page, field_type, field_name, field_value=None, bad_name=None, bad_value=None):
        entities_page.click_custom_data_add_new()
        parent = entities_page.find_custom_fields_items()[-1]
        assert entities_page.is_element_disabled(entities_page.find_custom_data_save())
        assert entities_page.is_input_error(entities_page.find_custom_data_new_field_type(parent))
        assert entities_page.is_input_error(entities_page.find_custom_data_new_field_name(parent))
        entities_page.select_custom_data_field_type(field_type, parent)
        if bad_name:
            entities_page.fill_custom_data_field_name(bad_name, parent)
            assert entities_page.is_input_error(entities_page.find_custom_data_new_field_name(parent))
        entities_page.fill_custom_data_field_name(field_name, parent)
        if bad_value:
            entities_page.fill_custom_data_value(bad_value, parent)
            assert entities_page.is_input_error(entities_page.find_custom_data_value(parent))
        if field_value:
            entities_page.fill_custom_data_value(field_value, parent)

    def _test_error_fields(self, entities_page, dup_field_name):
        entities_page.click_custom_data_edit()

        entities_page.click_custom_data_add_predefined()
        parent = entities_page.find_custom_fields_items()[-1]
        assert entities_page.is_element_disabled(entities_page.find_custom_data_save())
        assert entities_page.is_input_error(entities_page.find_custom_data_predefined_field(parent))
        entities_page.clear_custom_data_field()
        assert not entities_page.is_element_disabled(entities_page.find_custom_data_save())

        entities_page.click_custom_data_add_predefined()
        parent = entities_page.find_custom_fields_items()[-1]
        try:
            entities_page.select_custom_data_field(dup_field_name, parent)
        except NoSuchElementException:
            # Expected as the field cannot be set twice
            entities_page.close_dropdown()
        entities_page.clear_custom_data_field()
        assert not entities_page.is_element_disabled(entities_page.find_custom_data_save())

        entities_page.click_custom_data_add_new()
        parent = entities_page.find_custom_fields_items()[-1]
        entities_page.fill_custom_data_field_name(dup_field_name, parent)
        entities_page.is_custom_error(self.DUPLICATE_FIELD_ERROR)
        entities_page.fill_custom_data_field_name(dup_field_name.lower(), parent)
        entities_page.is_custom_error(self.DUPLICATE_FIELD_ERROR)
        entities_page.clear_custom_data_field()
        assert not entities_page.is_element_disabled(entities_page.find_custom_data_save())
        entities_page.save_custom_data()

    def _test_custom_data_bulk(self, entities_page, field_name):
        entities_page.switch_to_page()
        entities_page.click_query_wizard()
        entities_page.toggle_not()
        entities_page.select_query_adapter(entities_page.CUSTOM_ADAPTER_NAME)
        entities_page.select_query_field(entities_page.ID_FIELD, partial_text=False)
        entities_page.click_search()
        entities_page.wait_for_table_to_load()
        entities_page.click_row_checkbox()
        entities_page.click_row_checkbox(index=2)
        entities_page.open_custom_data_bulk()
        entities_page.click_custom_data_add_predefined()
        entities_page.select_custom_data_field(field_name)
        entities_page.fill_custom_data_value(self.CUSTOM_BULK_FIELD_VALUE)
        entities_page.save_custom_data_feedback(
            context=self.driver.find_element_by_css_selector(entities_page.CUSTOM_DATA_BULK_CONTAINER_CSS))
        entities_page.click_row_checkbox()
        entities_page.click_row_checkbox(index=2)
        entities_page.click_query_wizard()
        entities_page.toggle_not()
        entities_page.click_search()
        entities_page.wait_for_table_to_load()
        assert len(entities_page.get_all_data()) == 3

    def test_custom_data(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()

        self.devices_page.load_custom_data(self.devices_page.JSON_ADAPTER_FILTER)
        self._test_init_state(self.devices_page)
        self._test_first_data(self.devices_page, self.devices_page.FIELD_ASSET_NAME)
        self._test_new_fields(self.devices_page)
        self._test_error_fields(self.devices_page, self.devices_page.FIELD_ASSET_NAME)
        self._test_custom_data_bulk(self.devices_page, self.devices_page.FIELD_ASSET_NAME)

        self.users_page.load_custom_data(self.users_page.JSON_ADAPTER_FILTER)
        self._test_init_state(self.users_page)
        self._test_first_data(self.users_page, self.users_page.FIELD_USERNAME_TITLE)
        self._test_new_fields(self.users_page)
        self._test_error_fields(self.users_page, self.users_page.FIELD_USERNAME_TITLE)
        self._test_custom_data_bulk(self.users_page, self.users_page.FIELD_USERNAME_TITLE)

    def test_entity_data_search(self):
        """
        In the entity page under `General Data` there are tables that contain search input
        for example Installed Software for Kaseya adapter. This test checks that search works and returns
        information when used.
        """
        try:
            with KaseyaService().contextmanager(take_ownership=True):

                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(KASEYA_VSA_ADAPTER_NAME)
                self.adapters_page.click_adapter(KASEYA_VSA_ADAPTER_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                kaseya_client_details_2 = copy.copy(kaseya_client_details)
                kaseya_client_details_2.pop('verify_ssl')
                self.adapters_page.fill_creds(**kaseya_client_details_2)
                self.adapters_page.click_save()
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_server_green()
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                self.devices_page.wait_for_table_to_load()
                self.devices_page.click_query_wizard()
                self.devices_page.select_query_adapter(KASEYA_VSA_ADAPTER_NAME)
                self.devices_page.click_search()
                self.devices_page.wait_for_table_to_load()
                self.devices_page.click_table_container_first_row()
                self.devices_page.click_general_tab()
                tabs = self.devices_page.get_vertical_tab_elements()
                # Go over every tab, and over every header, pick the first rows data, and search it
                # Expect that row to show in search
                for tab in tabs:
                    tab.click()
                    # check if tab has a search element
                    try:
                        self.devices_page.fill_custom_data_search_input('')
                    except NoSuchElementException:
                        continue
                    rows = self.devices_page.get_all_entity_active_custom_data_tab_table_rows()
                    if len(rows) == 0:
                        continue
                    tr = rows[0]
                    for column in tr.columns:
                        self.devices_page.fill_custom_data_search_input('')
                        time.sleep(0.1)
                        self.devices_page.fill_custom_data_search_input(f'{column.strip()}')
                        tr2 = self.devices_page.get_all_entity_active_custom_data_tab_table_rows()[0]
                        assert tr2.columns == tr.columns
        finally:
            self.adapters_page.clean_adapter_servers(KASEYA_VSA_ADAPTER_NAME)
            self.wait_for_adapter_down(KASEYA_DOCKER_ADAPTER_NAME)
