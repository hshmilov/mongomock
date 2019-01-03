from ui_tests.pages.entities_page import EntitiesPage


class InstancesPage(EntitiesPage):
    ROOT_PAGE_CSS = 'li#instances.x-nav-item'
    CONNECT_NODE_ID = 'get-connection-string'

    @property
    def url(self):
        return f'{self.base_url}/instances'

    @property
    def root_page_css(self):
        return self.ROOT_PAGE_CSS

    def assert_screen_is_restricted(self):
        self.switch_to_page()
        self.find_element_by_text('You do not have permission to access the Instances screen')
        self.click_ok_button()

    def click_connect_node(self):
        self.click_button_by_id(self.CONNECT_NODE_ID)

    def is_connect_node_disabled(self):
        return self.is_element_disabled_by_id(self.CONNECT_NODE_ID)
