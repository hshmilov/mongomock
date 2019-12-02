import time

from ui_tests.tests.ui_consts import WINDOWS_QUERY_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestEntityResultsPerPage(TestBase):
    TWENTY_RESULTS_PER_PAGE = '20'
    FIFTY_RESULTS_PER_PAGE = '50'
    HUNDRED_RESULTS_PER_PAGE = '100'

    def change_values_count_entities_per_page_to_be_val(self, val):
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.wait_for_spinner_to_end()
        self.settings_page.select_values_count_entities_per_column(val)
        self.settings_page.click_save_gui_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

    def load_saved_queries_entities(self, entity_queries_page, val):
        saved_queries = self.driver.find_elements_by_css_selector('.x-query .filter button.x-button.link')[0]
        saved_queries.click()
        entity_queries_page.wait_for_table_to_load()
        time.sleep(2)
        # ensure that the 'defaultNumOfEntitiesPerPage' from System Settings does not affect the
        # "Saved Queries' page: 'devices/query/saved' or 'users/query/saved'
        assert entity_queries_page.find_active_page_size() == val

    @staticmethod
    def _switch_to_entity_page(entities_page):
        entities_page.switch_to_page()
        # refreshing the page to make sure the value is retrieved from default settings and not from state management
        entities_page.refresh()
        entities_page.wait_for_table_to_load()

    def _test_default_count_entities_per_page(self, entities_page, results_per_page):
        self._switch_to_entity_page(entities_page)
        # ensure that by default the 'defaultNumOfEntitiesPerPage' attribute in System Settings is set 20
        assert entities_page.find_active_page_size() == results_per_page

    def _test_count_entities_per_page(self, entities_page):
        self.devices_page.queries = ['AD Devices Missing Agents',
                                     'Users Information',
                                     'IPv4 Public Subnets',
                                     WINDOWS_QUERY_NAME]
        self.users_page.queries = ['Not Locked Users',
                                   'AD Disabled Users',
                                   'Users Created in Last Day',
                                   'Local Users']
        self._switch_to_entity_page(entities_page)
        # ensure that after refresh of the RESULTS PER PAGE (page size) active link
        # is set to the value of 'defaultNumOfEntitiesPerPage' // 100
        assert entities_page.find_active_page_size() == '100'
        entities_page.execute_saved_query(entities_page.queries[0])
        assert entities_page.find_active_page_size() == '100'
        if entities_page == self.devices_page:
            entity_queries_page = self.devices_queries_page
        else:
            entity_queries_page = self.users_queries_page
        # devices_queries_page || users_queries_page
        self.load_saved_queries_entities(entity_queries_page, self.TWENTY_RESULTS_PER_PAGE)
        # Click on the first Saved Query to load it in the entity 'users' or 'device' page
        windows_query_row = self.devices_queries_page.find_query_row_by_name(entities_page.queries[1])
        entity_queries_page.wait_for_spinner_to_end()
        windows_query_row.click()
        # Here the value of the value should be as the default
        entities_page.wait_for_table_to_load()
        assert entities_page.find_active_page_size() == self.HUNDRED_RESULTS_PER_PAGE
        # now click on a Page Size (of the RESULTS PER PAGE) different than the defaultNumOfEntitiesPerPage
        entities_page.select_page_size('50')
        entities_page.wait_for_table_to_load()
        entities_page.execute_saved_query(entities_page.queries[2])
        assert entities_page.find_active_page_size() == self.FIFTY_RESULTS_PER_PAGE
        self.load_saved_queries_entities(entity_queries_page, self.TWENTY_RESULTS_PER_PAGE)
        # ensure that the 'defaultNumOfEntitiesPerPage' from System Settings does not affect the
        # "Saved Queries' page: 'devices/query/saved' or 'users/query/saved'
        assert entity_queries_page.find_active_page_size() == self.TWENTY_RESULTS_PER_PAGE
        # Click on the first Saved Query to load it in the entity 'users' or 'device' page
        # self.devices_queries_page.click_row()
        windows_query_row = entity_queries_page.find_query_row_by_name(entities_page.queries[3])
        entity_queries_page.wait_for_spinner_to_end()
        windows_query_row.click()
        # Here the value of the value should be as the default
        entities_page.wait_for_table_to_load()
        assert entities_page.find_active_page_size() == self.FIFTY_RESULTS_PER_PAGE

    def test_change_values_count_entities_per_page(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self._test_default_count_entities_per_page(self.devices_page, self.TWENTY_RESULTS_PER_PAGE)
        # change the default value 'defaultNumOfEntitiesPerPage' to be 100
        self.change_values_count_entities_per_page_to_be_val(self.HUNDRED_RESULTS_PER_PAGE)
        self._test_count_entities_per_page(self.devices_page)
        # reset the default value 'defaultNumOfEntitiesPerPage' to be 20
        self.change_values_count_entities_per_page_to_be_val(self.TWENTY_RESULTS_PER_PAGE)
        self._test_default_count_entities_per_page(self.users_page, self.TWENTY_RESULTS_PER_PAGE)
        # change the default value 'defaultNumOfEntitiesPerPage' to be 100
        self.change_values_count_entities_per_page_to_be_val(self.HUNDRED_RESULTS_PER_PAGE)
        self._test_count_entities_per_page(self.users_page)
        # reset the default value 'defaultNumOfEntitiesPerPage' to be 20
        self.change_values_count_entities_per_page_to_be_val(self.TWENTY_RESULTS_PER_PAGE)
