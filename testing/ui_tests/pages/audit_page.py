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

    def get_last_activity_logs_messages(self, num_of_logs=20):
        self.switch_to_page()
        self.wait_for_table_to_load()
        self.select_page_size(num_of_logs)
        self.wait_for_table_to_load()
        table = self.driver.find_element_by_css_selector(self.TABLE_CLASS)
        # Use from index 1 to avoid selecting the table head
        rows = table.find_elements_by_tag_name('tr')[1:]
        if len(rows):
            return [row.find_elements_by_tag_name('td')[5].text for row in rows]
        return []
