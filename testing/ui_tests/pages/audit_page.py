from ui_tests.pages.entities_page import EntitiesPage
from gui.routes.labels.labels_catalog import LABELS_CATALOG

AUDIT_TABLE_COLUMNS = {
    'col_type': 'Type',
    'date': 'Date',
    'user': 'User',
    'action': 'Action',
    'category': 'Category',
    'message': 'Message'
}


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

    def verify_template_by_label_search(self, label: str, **kwargs):
        action = LABELS_CATALOG.get(label)
        msg = LABELS_CATALOG.get(f'{label}.template')
        self.fill_enter_table_search(action)
        audit = self.get_table_data(self.TABLE_CONTAINER_CSS, AUDIT_TABLE_COLUMNS.values())
        assert (audit[0][AUDIT_TABLE_COLUMNS['action']] == action and
                audit[0][AUDIT_TABLE_COLUMNS['message']] == msg.format(**kwargs))

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
