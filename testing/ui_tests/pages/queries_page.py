from services.axon_service import TimeoutException
from ui_tests.pages.page import Page


class QueriesPage(Page):
    QUERY_ROW_BY_NAME_XPATH = '//tr[child::td[child::div[text()=\'{query_name}\']]]'
    QUERY_FILTER_XPATH = './/td[position()=3]/div'

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
        # This is a sub-page and therefore is found by hovering the button leading to the parent
        try:
            self.wait_for_table_to_load()
        # might be on a page without a table
        except TimeoutException:
            pass
        self.hover_element_by_css(self.parent_root_page_css)
        super().switch_to_page()

    def find_query_row_by_name(self, query_name):
        return self.driver.find_element_by_xpath(self.QUERY_ROW_BY_NAME_XPATH.format(query_name=query_name))

    def find_query_filter_in_row(self, row_element):
        return row_element.find_element_by_xpath(self.QUERY_FILTER_XPATH).text

    def check_query_by_name(self, query_name):
        row = self.find_query_row_by_name(query_name)
        row.find_element_by_css_selector(self.CHECKBOX_CSS).click()

    def remove_selected_queries(self):
        self.find_element_by_text('Remove').click()
