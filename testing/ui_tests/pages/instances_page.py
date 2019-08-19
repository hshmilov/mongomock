import re

from selenium.common.exceptions import (ElementClickInterceptedException,
                                        NoSuchElementException,
                                        StaleElementReferenceException)

from axonius.utils.wait import wait_until
from ui_tests.pages.entities_page import EntitiesPage


class InstancesPage(EntitiesPage):
    ROOT_PAGE_CSS = 'li#instances.x-nav-item'
    CONNECT_NODE_ID = 'get-connection-string'
    NODE_JOIN_TOKEN_REGEX = '<axonius-hostname> (.*) '
    INSTANCES_ROW_BY_NAME_XPATH = '//tr[child::td[child::div[text()=\'{instance_name}\']]]'
    INSTANCES_USER_PASSWORD_XPATH = './/td[position()=6]/div'
    INSTANCES_HOSTNAME_XPATH = './/td[position()=3]/div'
    INSTANCES_IP_XPATH = './/td[position()=4]/div'

    @property
    def url(self):
        return f'{self.base_url}/instances'

    @property
    def root_page_css(self):
        return self.ROOT_PAGE_CSS

    def assert_screen_is_restricted(self):
        wait_until(self.switch_to_page_allowing_failure,
                   tolerated_exceptions_list=[ElementClickInterceptedException],
                   check_return_value=False)
        self.find_element_by_text('You do not have permission to access the Instances screen')
        self.click_ok_button()

    def click_connect_node(self):
        wait_until(lambda: self.click_button_by_id(self.CONNECT_NODE_ID),
                   tolerated_exceptions_list=[StaleElementReferenceException],
                   check_return_value=False)
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

        # Since the only adapter that duplicates and
        # initiates node name change (core/service.py search "Setting node_init_name")
        # is active directory this will have to wait until the duplicate from the node registers in core.
        # We have no way of knowing when this will happen but 10 minutes should do.
        wait_until(_refresh_and_get_row_by_node_name, check_return_value=False,
                   tolerated_exceptions_list=[NoSuchElementException],
                   total_timeout=60 * 10)

    def get_node_password(self, node_name):
        self.switch_to_page()
        self.refresh()
        instances_row = self.find_query_row_by_name(node_name)
        return instances_row.find_element_by_xpath(self.INSTANCES_USER_PASSWORD_XPATH).text

    def get_node_ip(self, node_name):
        self.switch_to_page()
        self.refresh()
        instances_row = self.find_query_row_by_name(node_name)
        return instances_row.find_element_by_xpath(self.INSTANCES_IP_XPATH).text

    def get_node_hostname(self, node_name):
        self.switch_to_page()
        self.refresh()
        instances_row = self.find_query_row_by_name(node_name)
        return instances_row.find_element_by_xpath(self.INSTANCES_HOSTNAME_XPATH).text

    def find_query_row_by_name(self, instance_name):
        return self.driver.find_element_by_xpath(self.INSTANCES_ROW_BY_NAME_XPATH.format(instance_name=instance_name))
