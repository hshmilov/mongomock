import logging
import time

from ui_tests.pages.entities_page import EntitiesPage
logger = logging.getLogger(f'axonius.{__name__}')


class QueriesPage(EntitiesPage):
    QUERY_ROW_BY_NAME_XPATH = '//tr[child::td[.//text()=\'{query_name}\']]'
    QUERY_NAME_BY_PART_XPATH = '//div[contains(text(), \'{query_name_part}\')]'
    SAFEGUARD_REMOVE_BUTTON_SINGLE = 'Remove Saved Query'
    SAFEGUARD_REMOVE_BUTTON_MULTI = 'Remove Saved Queries'
    RUN_QUERY_BUTTON_TEXT = 'Run Query'

    @property
    def url(self):
        raise NotImplementedError

    @property
    def root_page_css(self):
        raise NotImplementedError

    @property
    def parent_root_page_css(self):
        raise NotImplementedError

    def switch_to_page(self):
        logger.info(f'Switching to {self.parent_root_page_css}')
        self.wait_for_element_present_by_css(self.parent_root_page_css)
        self.driver.find_element_by_css_selector(self.parent_root_page_css).click()
        logger.info(f'Finished switching to {self.parent_root_page_css}')
        self.wait_for_table_to_load()
        self.click_button('Saved Queries', partial_class=True)

    def run_query(self):
        self.wait_for_element_present_by_css('.saved-query-panel')
        # wait for drawer animation end
        time.sleep(2)
        self.click_button(text=self.RUN_QUERY_BUTTON_TEXT)

    def find_query_row_by_name(self, query_name):
        return self.driver.find_element_by_xpath(self.QUERY_ROW_BY_NAME_XPATH.format(query_name=query_name))

    def check_query_by_name(self, query_name):
        row = self.find_query_row_by_name(query_name)
        row.find_element_by_css_selector(self.CHECKBOX_CSS).click()

    def remove_selected_queries(self, confirm=False):
        if confirm:
            self.remove_selected_with_safeguard(self.SAFEGUARD_REMOVE_BUTTON_SINGLE, self.SAFEGUARD_REMOVE_BUTTON_MULTI)
        else:
            self.remove_selected_with_safeguard()

    def enforce_selected_query(self):
        self.wait_for_element_present_by_css('.saved-query-panel')
        # wait for drawer animation end
        time.sleep(2)
        self.wait_for_element_present_by_css('.action-enforce').click()

    def find_query_name_by_part(self, query_name_part):
        return self.find_elements_by_xpath(self.QUERY_NAME_BY_PART_XPATH.format(query_name_part=query_name_part))
