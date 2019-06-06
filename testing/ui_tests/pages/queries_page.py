import logging
from ui_tests.pages.page import Page
logger = logging.getLogger(f'axonius.{__name__}')


class QueriesPage(Page):
    QUERY_ROW_BY_NAME_XPATH = '//tr[child::td[child::div[text()=\'{query_name}\']]]'
    QUERY_NAME_BY_PART_XPATH = '//div[contains(text(), \'{query_name_part}\')]'

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

    def find_query_row_by_name(self, query_name):
        return self.driver.find_element_by_xpath(self.QUERY_ROW_BY_NAME_XPATH.format(query_name=query_name))

    def check_query_by_name(self, query_name):
        row = self.find_query_row_by_name(query_name)
        row.find_element_by_css_selector(self.CHECKBOX_CSS).click()

    def remove_selected_queries(self):
        self.find_element_by_text(self.REMOVE_BUTTON).click()
        self.wait_for_element_absent_by_css('.x-checkbox.x-checked')

    def enforce_selected_query(self):
        self.find_element_by_text(self.test_base.enforcements_page.NEW_ENFORCEMENT_BUTTON).click()

    def find_query_name_by_part(self, query_name_part):
        return self.find_elements_by_xpath(self.QUERY_NAME_BY_PART_XPATH.format(query_name_part=query_name_part))
