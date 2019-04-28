import re

from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until
from ui_tests.pages.entities_page import EntitiesPage


class InstancesPage(EntitiesPage):
    ROOT_PAGE_CSS = 'li#instances.x-nav-item'
    CONNECT_NODE_ID = 'get-connection-string'
    NODE_JOIN_TOKEN_REGEX = '<axonius-hostname> (.*) '
    INSTANCES_ROW_BY_NAME_XPATH = '//tr[child::td[child::div[text()=\'{instance_name}\']]]'
    INSTANCES_USER_PASSWORD_XPATH = './/td[position()=4]/div'

    @property
    def url(self):
        return f'{self.base_url}/instances'

    @property
    def root_page_css(self):
        return self.ROOT_PAGE_CSS

    def assert_screen_is_restricted(self):
        self.switch_to_page_allowing_failure()
        self.find_element_by_text('You do not have permission to access the Instances screen')
        self.click_ok_button()

    def click_connect_node(self):
        self.click_button_by_id(self.CONNECT_NODE_ID)
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)

    def is_connect_node_disabled(self):
        return self.is_element_disabled_by_id(self.CONNECT_NODE_ID)

    def get_node_join_token(self):
        self.switch_to_page()
        self.click_connect_node()
        connection_details = self.find_element_by_text('How to connect a new node').text
        self.click_ok_button()
        return re.search(self.NODE_JOIN_TOKEN_REGEX, connection_details).group(1)

    def wait_until_node_appears_in_table(self, node_name):
        def _refresh_and_get_row_by_node_name():
            self.switch_to_page()
            self.refresh()
            return self.find_query_row_by_name(node_name)

        wait_until(_refresh_and_get_row_by_node_name, check_return_value=False, exc_list=[NoSuchElementException])

    def get_node_password(self, node_name):
        self.switch_to_page()
        self.refresh()
        instances_row = self.find_query_row_by_name(node_name)
        return instances_row.find_element_by_xpath(self.INSTANCES_USER_PASSWORD_XPATH).text

    def find_query_row_by_name(self, instance_name):
        return self.driver.find_element_by_xpath(self.INSTANCES_ROW_BY_NAME_XPATH.format(instance_name=instance_name))
