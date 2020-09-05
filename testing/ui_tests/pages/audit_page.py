from ui_tests.pages.entities_page import EntitiesPage


class AuditPage(EntitiesPage):
    @property
    def url(self):
        return f'{self.base_url}/audit'

    @property
    def root_page_css(self):
        return 'li#audit.x-nav-item'

    def get_last_activity_log_action(self):
        table = self.driver.find_element_by_css_selector(self.TABLE_CLASS)
        # Use from index 1 to avoid selecting the table head
        rows = table.find_elements_by_tag_name('tr')[1:]
        if len(rows):
            return rows[0].find_elements_by_tag_name('td')[3].text
        return ''
