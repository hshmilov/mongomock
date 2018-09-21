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
        self.hover_element_by_css(self.parent_root_page_css)
        super().switch_to_page()

    def find_query_row_by_name(self, query_name):
        return self.driver.find_element_by_xpath(self.QUERY_ROW_BY_NAME_XPATH.format(query_name=query_name))

    def find_query_filter_in_row(self, row_element):
        return row_element.find_element_by_xpath(self.QUERY_FILTER_XPATH).text
