import pytest
from selenium.common.exceptions import NoSuchElementException

from ui_tests.pages.entities_page import EntitiesPage


class DevicesPage(EntitiesPage):
    FIELD_NETWORK_INTERFACES_IPS = 'Network Interfaces: IPs'
    FIELD_NETWORK_INTERFACES = 'Network Interfaces'
    FIELD_OS_TYPE = 'OS: Type'
    FIELD_TAGS = 'Tags'
    FIELD_ADAPTERS = 'Adapters'
    FIELD_LAST_SEEN = 'Last Seen'
    FIELD_HOSTNAME_TITLE = 'Host Name'
    FIELD_HOSTNAME_NAME = 'hostname'
    FIELD_ASSET_NAME = 'Asset Name'
    FIELD_SAVED_QUERY = 'Saved Query'
    FIELD_AVSTATUS = 'AvStatus'
    FIELD_AD_NAME = 'AD name'
    VALUE_SAVED_QUERY_WINDOWS = 'Windows Operating System'
    VALUE_SAVED_QUERY_LINUX = 'Linux Operating System'
    VALUE_OS_WINDOWS = 'Windows'
    TAG_CHECKBOX_CSS = 'div.modal-container.w-xl > div.modal-body > div > div.x-checkbox-list > div > div'
    TAG_SAVE_BUTTON_CSS = 'div.modal-container.w-xl > div.modal-footer > div > button:nth-child(2)'
    LABELS_TEXTBOX_CSS = 'div.modal-body > div > div.search-input > input'
    TAGGING_1_DEVICE_MESSAGE = 'Tagged 1 devices!'
    TAGGING_1_DEVICE_XPATH = f'.//div[contains(@class, \'text-center\') and .//text()=\'{TAGGING_1_DEVICE_MESSAGE}\']'
    MULTI_LINE_CSS = 'div.x-data-table.multiline'
    FILTER_HOSTNAME = 'specific_data.data.hostname == regex("{filter_value}", "i")'

    @property
    def url(self):
        return f'{self.base_url}/devices'

    @property
    def root_page_css(self):
        return 'li#devices.x-nested-nav-item'

    def click_tag_save_button(self):
        self.driver.find_element_by_css_selector(self.TAG_SAVE_BUTTON_CSS).click()

    def check_if_table_is_multi_line(self):
        self.wait_for_element_present_by_css(self.MULTI_LINE_CSS)

    def check_if_adapter_tab_not_exist(self):
        with pytest.raises(NoSuchElementException):
            self.driver.find_element_by_css_selector('#specific')

    def wait_for_success_tagging_message(self):
        self.wait_for_element_present_by_xpath(self.TAGGING_1_DEVICE_XPATH)
        self.wait_for_element_absent_by_xpath(self.TAGGING_1_DEVICE_XPATH)

    def open_tag_dialog(self):
        self.click_button('Actions', partial_class=True, should_scroll_into_view=False)
        self.click_actions_tag_button()

    def add_new_tag(self, tag_text):
        self.open_tag_dialog()
        self.fill_text_field_by_css_selector(self.LABELS_TEXTBOX_CSS, tag_text)
        self.wait_for_element_present_by_css(self.TAG_CHECKBOX_CSS).click()
        self.click_tag_save_button()
        self.wait_for_success_tagging_message()
        self.wait_for_spinner_to_end()

    def remove_first_tag(self):
        self.open_tag_dialog()
        self.wait_for_element_present_by_css(self.TAG_CHECKBOX_CSS).click()
        self.click_tag_save_button()
        self.wait_for_success_tagging_message()

    def remove_tag(self, text):
        self.open_tag_dialog()
        self.find_element_by_text(text).click()
        self.click_tag_save_button()
        self.wait_for_success_tagging_message()

    def get_first_tag_text(self):
        return self.get_first_row_tags().splitlines()[0]

    def get_first_row_tags(self):
        return self.driver.find_elements_by_css_selector(self.TABLE_FIRST_ROW_TAG_CSS)[0].text

    def assert_screen_is_restricted(self):
        self.switch_to_page()
        self.find_element_by_text('You do not have permission to access the Devices screen')
        self.click_ok_button()

    def query_hostname_contains(self, string):
        self.run_filter_query(self.FILTER_HOSTNAME.format(filter_value=string))
