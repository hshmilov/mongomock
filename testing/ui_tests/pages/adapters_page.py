from collections import namedtuple

from ui_tests.pages.entities_page import EntitiesPage

# NamedTuple doesn't need to be uppercase
# pylint: disable=C0103
Adapter = namedtuple('Adapter', 'name description')


class AdaptersPage(EntitiesPage):
    ROOT_PAGE_CSS = 'li#adapters.x-nested-nav-item'
    SEARCH_TEXTBOX_CSS = 'div.search-input > input.input-value'
    TABLE_ROW_CLASS = 'table-row'

    @property
    def url(self):
        return f'{self.base_url}/adapter'

    @property
    def root_page_css(self):
        return self.ROOT_PAGE_CSS

    def search(self, text):
        text_box = self.driver.find_element_by_css_selector(self.SEARCH_TEXTBOX_CSS)
        self.fill_text_by_element(text_box, text)

    def get_adapter_list(self):
        result = []

        adapter_table = self.driver.find_elements_by_class_name(self.TABLE_ROW_CLASS)

        # Skip the title row
        adapter_table = adapter_table[1:]

        for adapter_element in adapter_table:
            name, description = adapter_element.text.split('\n', 1)
            result.append(Adapter(name=name, description=description))

        return result

    def click_adapter(self, adapter_name):
        self.click_button(adapter_name, button_class='title', button_type='div', call_space=False)
