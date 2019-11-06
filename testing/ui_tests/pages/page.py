import logging
import os
import time
import urllib.parse
from tempfile import NamedTemporaryFile

from retrying import retry
from selenium.common.exceptions import (ElementNotVisibleException,
                                        NoSuchElementException,
                                        StaleElementReferenceException,
                                        WebDriverException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from axonius.utils.parsing import normalize_timezone_date
from services.axon_service import TimeoutException
from ui_tests.tests.ui_consts import TEMP_FILE_PREFIX

logger = logging.getLogger(f'axonius.{__name__}')

# arguments[0] is the argument being passed by execute_script of selenium's driver
SCROLL_TO_TOP = '''
var containerElement = window;
if (arguments[1]) {
    containerElement = document.querySelector(arguments[1])
}

(function(container){container.scrollTo(0,0)})(containerElement)
'''
SCROLL_INTO_VIEW_JS = '''
var containerElement = window;
if (arguments[1]) {
    containerElement = document.querySelector(arguments[1])
}

return (function(el, container){
    container.scrollTo(0, 0);
    var old_scroll = container == window ? container.scrollY : container.scrollTop;
    while(true) {
        var box = el.getBoundingClientRect();
        var el_in_pos = document.elementFromPoint(box.left + box.width/2, box.top + box.height/2);
        if (el_in_pos === el) {
            return true;
        }
        if (container === window) {
            if (el_in_pos && (el_in_pos.contains(el) || el.contains(el_in_pos))) {
                return true;
            }
        } else {
            if (container.contains(el_in_pos) && (el_in_pos.contains(el) || el.contains(el_in_pos))) {
                return true;
            }
        }
        container.scrollBy(0, 40);
        if (old_scroll === (container === window ? container.scrollY : container.scrollTop)) {
            return false;
        }
        old_scroll = container === window ? container.scrollY : container.scrollTop;
    }
})(arguments[0], containerElement);
'''

BUTTON_DEFAULT_TYPE = 'button'
BUTTON_DEFAULT_CLASS = 'x-button'
BUTTON_TYPE_A = 'a'
PAGE_BODY = '.x-page > .body'
TAB_BODY = '.x-tabs > .body'
TOGGLE_CHECKED_CLASS = 'x-checkbox checked'
TOASTER_BY_TEXT_XPATH = '//div[@class=\'x-toast\']//div[@class=\'content\' and text()=\'{toast_text}\']'
TABLE_SPINNER_NOT_DISPLAYED_XPATH = '//div[@class=\'v-spinner\' and @style=\'display: none;\']'
RETRY_WAIT_FOR_ELEMENT = 150
SLEEP_INTERVAL = 0.2


class TableRow:
    """
    TableRow - container for a single row in entity custom data table
    """

    def __init__(self, element, headers=None):
        self.element = element
        if headers is None:
            headers = []
        self.headers = headers
        self.columns = element.text.split('\n')


class Page:
    LOADING_SPINNER_CSS = '.v-spinner-bg'
    LOADING_SPINNER_CSS2 = '.v-spinner'
    CHECKBOX_XPATH_TEMPLATE = '//div[child::label[text()=\'{label_text}\']]/div[contains(@class, \'x-checkbox\')]'
    CHECKBOX_WITH_LABEL_XPATH = '//div[contains(@class, \'x-checkbox\') and child::label[text()=\'{label_text}\']]'
    CHECKBOX_WITH_SIBLING_LABEL_XPATH = '//div[contains(@class, \'x-checkbox\') and ' \
                                        'preceding-sibling::label[text()=\'{label_text}\']]'
    CHECKBOX_CSS = '.x-checkbox .checkbox-container'
    DIV_BY_LABEL_TEMPLATE = '//div[child::label[text()=\'{label_text}\']]'
    DROPDOWN_OVERLAY_CSS = '.x-dropdown-bg'
    MODAL_OVERLAY_CSS = '.modal-overlay'
    FEEDBACK_MODAL_MESSAGE_XPATH = './/div[contains(@class, \'t-center\') and .//text()=\'{message}\']'
    CANCEL_BUTTON = 'Cancel'
    SAVE_BUTTON = 'Save'
    SAVE_AND_CONNECT_BUTTON = 'Save and Connect'
    SAVE_AS_BUTTON = 'Save as'
    OK_BUTTON = 'OK'
    REMOVE_BUTTON = 'Remove'
    DELETE_BUTTON = 'Delete'
    ACTIONS_BUTTON = 'Actions'
    CONFIRM_BUTTON = 'Confirm'
    DISABLED_BUTTON_XPATH = './/button[@class=\'x-button disabled\' and .//text()=\'{button_text}\']'
    VERTICAL_TABS_CSS = '.x-tabs.vertical .header .header-tab'

    NAMED_TAB_XPATH = '//div[@class=\'x-tabs\']/ul/li[contains(@class, "header-tab")]//div[text()=\'{tab_title}\']'
    TABLE_ROWS_CSS = 'tbody .x-table-row.clickable'
    TABLE_COUNTER = 'div.count'
    UPLOADING_FILE_CSS = '//div[@class=\'name-placeholder\' and text()=\'Uploading...\']'

    CUSTOM_ADAPTER_NAME = 'Custom Data'

    DATEPICKER_INPUT_CSS = '.md-datepicker .md-input'
    DATEPICKER_OVERLAY_CSS = '.md-datepicker-overlay'
    CHIPS_WITH_LABEL_XPATH = '//div[label[text()=\'{label_text}\']]' \
                             '/div[contains(@class, \'md-chips\')]//input[@type=\'text\']'

    CHIPS_VALUES_WITH_LABEL_XPATH = '//div[label[text()=\'{label_text}\']]' \
                                    '/div[contains(@class, \'md-chips\')]//div[contains(@class, \'md-chip\')]'

    CHECKBOX_BY_PARENT_ID = '//div[@id=\'{parent_id}\']/div[contains(@class, \'x-checkbox\')]' \
                            '//input[@type=\'checkbox\']'
    TABLE_ALL_CHECKBOX_CSS = 'thead tr th:nth-child(1) .x-checkbox'
    TABLE_ROW_CHECKBOX_CSS = 'tbody .x-table-row.clickable:nth-child({child_index}) td:nth-child(1) .x-checkbox'
    TABLE_ROW_TEXT_CELL_CSS = 'tbody .x-table-row.clickable:nth-child({row_index}) td:nth-child({cell_index}) div'

    FIELD_WITH_LABEL_XPATH = '//div[child::label[text()=\'{label_text}\']]/div[contains(@class, \'md-field\')]'
    DROPDOWN_TAGS_CSS = 'div.x-dropdown.x-select.all-tags'
    DROPDOWN_TAGS_VALUE_CSS = 'div.x-dropdown.x-select.all-tags div.trigger-text'
    DROPDOWN_TEXT_BOX_CSS = 'div.x-search-input.x-select-search > input'
    DROPDOWN_SELECTED_OPTIONS_CSS = 'div.x-select-options'
    DROPDOWN_SELECTED_OPTION_CSS = 'div.x-select-options > div.x-select-option'
    DROPDOWN_SELECT_OPTION_CSS = 'div.x-select-options > div.x-select-option[title=\'{title}\']'
    DROPDOWN_NEW_OPTION_CSS = 'div.x-select-options + div.x-footer-option'

    TAB_HEADER_XPATH = '//div[contains(@class, \'x-tabs\')]/ul/li[contains(@class, \'header-tab\') and ' \
                       './/text()=\'{tab_title}\']'

    RENAME_TAB_INPUT_ID = 'rename_tab'

    SEARCH_INPUT_CSS = '.x-search-input .input-value'

    CUSTOM_DATA_SEARCH_INPUT = '.body .x-tabs.vertical .body .x-tab.active .x-search-input input'
    TABLE_PAGE_SIZE_ACTIVE_XPATH = '//div[@class=\'x-pagination\']/div[@class=\'x-sizes\']' \
                                   '/div[@class=\'x-link active\']'

    def __init__(self, driver, base_url, test_base, local_browser: bool):
        self.driver = driver
        self.base_url = base_url
        self.local_browser = local_browser
        self.ui_tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../', '../'))
        self.test_base = test_base

    def cleanup(self):
        pass

    @property
    def url(self):
        raise NotImplementedError

    @property
    def current_url(self):
        return self.driver.current_url

    @property
    def root_page_css(self):
        raise NotImplementedError

    def refresh(self):
        url = ''
        try:
            url = self.url
        except NotImplementedError:
            pass
        full_url = urllib.parse.urljoin(self.base_url, url)
        self.driver.get(full_url)

    @staticmethod
    def has_class(element, lookup_class):
        classes = element.get_attribute('class')
        for c in classes.split(' '):
            if c == lookup_class:
                return True
        return False

    def switch_to_page(self):
        self.switch_to_page_allowing_failure()
        if self.url != self.driver.current_url:
            logger.info(f'Failed at first attempt to switch to {self.root_page_css}, '
                        f'current url: {self.driver.current_url}')
            time.sleep(1)
            self.wait_for_element_present_by_css(self.root_page_css).click()
            if self.url != self.driver.current_url:
                logger.error(f'Could not switch to {self.root_page_css}, current url: {self.driver.current_url}')
                return
        logger.info(f'Finished switching to {self.root_page_css} successfully')

    def switch_to_page_allowing_failure(self):
        logger.info(f'Switching to {self.root_page_css}')
        self.wait_for_element_present_by_css(self.root_page_css).click()

    def scroll_to_top(self):
        self.driver.execute_script('window.scrollTo(0, 0)')

    @staticmethod
    def clear_element(element):
        element.send_keys(Keys.LEFT_CONTROL, 'a')
        element.send_keys(Keys.BACKSPACE)
        element.send_keys(Keys.LEFT_ALT, Keys.BACKSPACE)
        element.clear()
        while element.text != '' or \
                (element.get_attribute('value') is not None and element.get_attribute('value') != ''):
            element.send_keys(Keys.BACKSPACE)

    @staticmethod
    def clear_element_text(element):
        for _ in range(1000):
            element.send_keys(Keys.BACKSPACE)
            if element.get_attribute('value') == '':
                break

    @staticmethod
    def extract_first_int(text):
        return [int(s) for s in text if s.isdigit()][0]

    def fill_text_field_by_element_id(self, element_id, value, context=None, last_field=False):
        return self.fill_text_field_by(By.ID, element_id, value, context, last_field=last_field)

    def fill_text_field_by_name(self, name, value, context=None):
        return self.fill_text_field_by(By.NAME, name, value, context)

    def fill_text_field_by_tag_name(self, tag_name, value, context=None):
        return self.fill_text_field_by(By.TAG_NAME, tag_name, value, context)

    def fill_text_field_by_css_selector(self, css_selector, value, context=None):
        return self.fill_text_field_by(By.CSS_SELECTOR, css_selector, value, context)

    def fill_text_field_by(self, by, by_value, value, context=None, last_field=False):
        try:
            base = context if context is not None else self.driver
            if last_field:
                element = base.find_elements(by=by, value=by_value)[-1]
            else:
                element = base.find_element(by=by, value=by_value)
            self.fill_text_by_element(element, value)
        except WebDriverException:
            logger.exception(f'Failed to fill {by_value}')
            raise

    def fill_text_by_element(self, element, text, clear=True):
        if clear:
            self.clear_element_text(element)
        if not isinstance(text, str):
            text = repr(text)
        self.send_keys(element, text)

    @classmethod
    def send_keys(cls, element, val):
        element.send_keys(val)

    @staticmethod
    def get_button_xpath(text, button_type=BUTTON_DEFAULT_TYPE, button_class=BUTTON_DEFAULT_CLASS, partial_class=False):
        button_xpath_template = './/{}[@class=\'{}\' and .//text()=\'{}\']'
        if partial_class:
            button_xpath_template = './/{}[contains(@class, \'{}\') and .//text()=\'{}\']'
        xpath = button_xpath_template.format(button_type, button_class, text)
        return xpath

    def get_button(self, text, button_type=BUTTON_DEFAULT_TYPE, button_class=BUTTON_DEFAULT_CLASS, partial_class=False,
                   context=None):
        base = context if context is not None else self.driver
        xpath = self.get_button_xpath(text, button_type=button_type, button_class=button_class,
                                      partial_class=partial_class)
        return base.find_element_by_xpath(xpath)

    # this is a special case where the usual get_button doesn't work, name will be changed later
    def get_special_button(self, text):
        elems = self.driver.find_elements_by_css_selector('button.x-button')
        for elem in elems:
            if elem.text == text:
                return elem
        return None

    def click_button_by_id(self,
                           button_id,
                           **kwargs):
        button = self.driver.find_element_by_id(button_id)
        return self.handle_button(button, **kwargs)

    def handle_button(self,
                      button,
                      call_space=True,
                      ignore_exc=False,
                      with_confirmation=False,
                      should_scroll_into_view=True,
                      scroll_into_view_container=None):
        if should_scroll_into_view:
            self.scroll_into_view(button, window=scroll_into_view_container)
        if call_space:
            button.send_keys(Keys.SPACE)
        else:
            try:
                button.click()
                logger.info(f'Clicked on {button}')
            except WebDriverException:
                logger.info(f'Failed clicking on {button}')
                if not ignore_exc:
                    raise
        if with_confirmation:
            raise NotImplementedError
        return button

    def click_button(self,
                     text,
                     button_type=BUTTON_DEFAULT_TYPE,
                     button_class=BUTTON_DEFAULT_CLASS,
                     partial_class=False,
                     context=None,
                     **kwargs):
        button = self.get_button(text,
                                 button_type=button_type,
                                 button_class=button_class,
                                 partial_class=partial_class,
                                 context=context)

        return self.handle_button(button, **kwargs)

    @retry(stop_max_attempt_number=5, wait_fixed=500)
    def scroll_into_view(self, element, window=None):
        try:
            self.scroll_into_view_no_retry(element, window)
        except StaleElementReferenceException:
            logger.exception(f'Failed to scroll down into element {element}')
            raise

    def scroll_into_view_no_retry(self, element, window=None):
        self.driver.execute_script(SCROLL_TO_TOP, window)
        result = self.driver.execute_script(SCROLL_INTO_VIEW_JS, element, window)
        assert result, 'Failed to scroll'

    def wait_for_element_present_by_css(self,
                                        css,
                                        element=None,
                                        retries=RETRY_WAIT_FOR_ELEMENT,
                                        interval=SLEEP_INTERVAL,
                                        is_displayed=False):
        return self.wait_for_element_present(By.CSS_SELECTOR, css, element, retries, interval, is_displayed)

    def wait_for_element_present_by_xpath(self,
                                          xpath,
                                          element=None,
                                          retries=RETRY_WAIT_FOR_ELEMENT,
                                          interval=SLEEP_INTERVAL):
        return self.wait_for_element_present(By.XPATH, xpath, element, retries, interval)

    def wait_for_element_present_by_id(self,
                                       element_id,
                                       element=None,
                                       retries=RETRY_WAIT_FOR_ELEMENT,
                                       interval=SLEEP_INTERVAL):
        return self.wait_for_element_present(By.ID, element_id, element, retries, interval)

    def wait_for_element_present(self,
                                 by,
                                 value,
                                 parent=None,
                                 retries=RETRY_WAIT_FOR_ELEMENT,
                                 interval=SLEEP_INTERVAL,
                                 is_displayed=False):
        for _ in range(retries):
            try:
                element = self.find_element(by, value, parent)
                if element and (not is_displayed or element.is_displayed()):
                    return element
            except NoSuchElementException:
                pass
            time.sleep(interval)
        raise TimeoutException(f'Timeout while waiting for {value}')

    def wait_for_element_absent_by_id(self, element_id, *vargs, **kwargs):
        self.wait_for_element_absent(By.ID, element_id, *vargs, **kwargs)

    def wait_for_element_absent_by_css(self, css_selector, *vargs, **kwargs):
        self.wait_for_element_absent(By.CSS_SELECTOR, css_selector, *vargs, **kwargs)

    def wait_for_element_absent_by_xpath(self, xpath, *vargs, **kwargs):
        self.wait_for_element_absent(By.XPATH, xpath, *vargs, **kwargs)

    def wait_for_element_absent(self,
                                by,
                                value,
                                element=None,
                                retries=RETRY_WAIT_FOR_ELEMENT,
                                interval=SLEEP_INTERVAL):
        for _ in range(retries):
            try:
                absent_element = self.find_element(by, value, element)
                if not absent_element:
                    return
                if 'none' in absent_element.get_attribute('style'):
                    return
            except (NoSuchElementException, StaleElementReferenceException):
                return
            time.sleep(interval)
        raise TimeoutException(f'Timeout while waiting for {value} to disappear')

    def wait_for_toaster_to_end(self,
                                text,
                                retries=RETRY_WAIT_FOR_ELEMENT,
                                interval=SLEEP_INTERVAL):
        for _ in range(retries):
            try:
                toaster = self.find_toaster(text)
                if not toaster:
                    return True
            except (NoSuchElementException, StaleElementReferenceException):
                return True
            time.sleep(interval)
        raise TimeoutException(f'Timeout while waiting for toaster {text} to disappear')

    def find_element(self, how, what, element=None):
        if element is None:
            return self.driver.find_element(by=how, value=what)
        return element.find_element(by=how, value=what)

    def find_toaster(self, text):
        return self.driver.find_element_by_xpath(TOASTER_BY_TEXT_XPATH.format(toast_text=text))

    # this is currently a bit duplicated, will fix later
    def wait_for_toaster(self,
                         text,
                         retries=RETRY_WAIT_FOR_ELEMENT,
                         interval=SLEEP_INTERVAL):
        for _ in range(retries):
            try:
                toaster = self.find_toaster(text)
                if toaster:
                    return toaster
            except NoSuchElementException:
                pass
            time.sleep(interval)
        raise TimeoutException(f'Timeout while waiting for {text}')

    def find_element_by_text(self, text, element=None):
        # Selenium using XPATH 1.0 which doesn't support escaping of string literals
        if not element:
            element = self.driver
        try:
            if '"' in text and '\'' in text:
                raise ValueError(f'{text} contains both \' and "')
            if '"' in text:
                return element.find_element_by_xpath(f'//*[contains(text(), \'{text}\')]')
            return element.find_element_by_xpath(f'//*[contains(text(), "{text}")]')
        except ElementNotVisibleException:
            logger.info(f'Failed to find element with text {text}')

    def find_element_parent_by_text(self, text, element=None):
        # Selenium using XPATH 1.0 which doesn't support escaping of string literals
        if not element:
            element = self.driver
        if '"' in text and '\'' in text:
            raise ValueError(f'{text} contains both \' and "')
        if '"' in text:
            return element.find_element_by_xpath(f'//*[contains(text(), \'{text}\')]/..')
        return element.find_element_by_xpath(f'//*[contains(text(), "{text}")]/..')

    def find_element_preceding_by_text(self, text, element=None):
        # Selenium using XPATH 1.0 which doesn't support escaping of string literals
        if not element:
            element = self.driver
        if '"' in text and '\'' in text:
            raise ValueError(f'{text} contains both \' and "')
        if '"' in text:
            return element.find_element_by_xpath(f'//*[contains(text(), \'{text}\')]/preceding-sibling::div')
        return element.find_element_by_xpath(f'//*[contains(text(), "{text}")]/preceding-sibling::div')

    def find_element_following_label(self, text, element=None):
        # Selenium using XPATH 1.0 which doesn't support escaping of string literals
        if not element:
            element = self.driver
        if '"' in text and '\'' in text:
            raise ValueError(f'{text} contains both \' and "')
        if '"' in text:
            return element.find_element_by_xpath(f'//*[contains(text(), \'{text}\')]/following::div')
        return element.find_element_by_xpath(f'//*[contains(text(), "{text}")]/following::div')

    def find_elements_by_xpath(self, xpath, element=None):
        if not element:
            element = self.driver
        return element.find_elements(by=By.XPATH, value=xpath)

    def find_chips_by_label(self, label_text):
        xpath = self.CHIPS_WITH_LABEL_XPATH.format(label_text=label_text)
        return self.driver.find_element_by_xpath(xpath)

    def find_chips_values_by_label(self, label_text):
        xpath = self.CHIPS_VALUES_WITH_LABEL_XPATH.format(label_text=label_text)
        return self.find_elements_by_xpath(xpath)

    # this is currently a bit duplicated, will fix later
    def wait_for_element_present_by_text(self,
                                         text,
                                         element=None,
                                         retries=RETRY_WAIT_FOR_ELEMENT,
                                         interval=SLEEP_INTERVAL):
        for _ in range(retries):
            try:
                element = self.find_element_by_text(text, element=element)
                if element:
                    return element
            except NoSuchElementException:
                pass
            time.sleep(interval)
        raise TimeoutException(f'Timeout while waiting for {text}')

    def wait_for_element_absent_by_text(self,
                                        text,
                                        element=None,
                                        retries=RETRY_WAIT_FOR_ELEMENT,
                                        interval=SLEEP_INTERVAL):
        for _ in range(retries):
            try:
                element = self.find_element_by_text(text, element=element)
                if not element:
                    return
            except (NoSuchElementException, StaleElementReferenceException):
                return
            time.sleep(interval)
        raise TimeoutException(f'Timeout while waiting for {text} to disappear')

    @staticmethod
    def is_toggle_selected(toggle):
        return TOGGLE_CHECKED_CLASS in toggle.get_attribute('class')

    def click_toggle_button(self,
                            toggle,
                            make_yes=True,
                            ignore_exc=False,
                            scroll_to_toggle=True,
                            window=PAGE_BODY):
        is_selected = self.is_toggle_selected(toggle)

        if (make_yes and not is_selected) or (not make_yes and is_selected):
            try:
                if scroll_to_toggle:
                    self.scroll_into_view(toggle, window)
                toggle.click()
                return True
            except WebDriverException:
                if not ignore_exc:
                    raise

        assert self.is_toggle_selected(toggle) == make_yes
        return False

    def select_option(self,
                      dropdown_css_selector,
                      text_box_css_selector,
                      selected_option_css_selector,
                      choice,
                      parent=None,
                      partial_text=True):
        if not parent:
            parent = self.driver
        parent.find_element_by_css_selector(dropdown_css_selector).click()
        text_box = self.driver.find_element_by_css_selector(text_box_css_selector)
        self.send_keys(text_box, choice)
        if partial_text:
            self.driver.find_element_by_css_selector(selected_option_css_selector).click()
        else:
            next(el for el in self.driver.find_elements_by_css_selector(selected_option_css_selector) if
                 el.text == choice).click()

    def enter_option(self,
                     dropdown_css_selector,
                     text_box_css_selector,
                     choice,
                     parent=None):
        if not parent:
            parent = self.driver
        parent.find_element_by_css_selector(dropdown_css_selector).click()
        text_box = self.driver.find_element_by_css_selector(text_box_css_selector)
        self.send_keys(text_box, choice)
        text_box.send_keys(Keys.ENTER)

    def select_option_from_multiple(self,
                                    index,
                                    dropdown_css_selector,
                                    text_box_css_selector,
                                    selected_option_css_selector,
                                    choice,
                                    parent=None,
                                    partial_text=True):
        if not parent:
            parent = self.driver
        parent.find_elements_by_css_selector(dropdown_css_selector)[index].click()
        text_box = self.driver.find_element_by_css_selector(text_box_css_selector)
        self.send_keys(text_box, choice)
        if partial_text:
            self.driver.find_element_by_css_selector(selected_option_css_selector).click()
        else:
            next(el for el in self.driver.find_elements_by_css_selector(selected_option_css_selector) if
                 el.text == choice).click()

    def select_option_without_search(self,
                                     dropdown_css_selector,
                                     selected_options_css_selector,
                                     text,
                                     parent=None):
        if not parent:
            parent = self.driver
        parent.find_element_by_css_selector(dropdown_css_selector).click()
        options = self.driver.find_elements_by_css_selector(selected_options_css_selector)
        for option in options:
            if option.text == text:
                option.click()
                return option
        return None

    def select_option_without_search_from_multiple(self,
                                                   index,
                                                   dropdown_css_selector,
                                                   selected_options_css_selector,
                                                   text,
                                                   parent=None):
        if not parent:
            parent = self.driver
        parent.find_elements_by_css_selector(dropdown_css_selector)[index].click()
        options = self.driver.find_elements_by_css_selector(selected_options_css_selector)
        for option in options:
            if option.text == text:
                option.click()
                return option
        raise AssertionError(f'Could not find option {text}')

    @staticmethod
    def key_down_enter(element):
        element.send_keys(Keys.ENTER)

    @staticmethod
    def key_down_arrow_down(element):
        element.send_keys(Keys.ARROW_DOWN)

    def wait_for_spinner_to_end(self):
        # This method wants to wait for the spinner to appear and finish.

        # It's impossible to wait for the spinner to begin
        # because it might already be gone when we got here, so we optimistically
        # wait a bit to simulate waiting for the spinner to appear.
        time.sleep(0.3)

        self.wait_for_element_absent_by_css(self.LOADING_SPINNER_CSS)
        self.wait_for_element_absent_by_css(self.LOADING_SPINNER_CSS2)

    def wait_for_table_to_load(self, retries=RETRY_WAIT_FOR_ELEMENT, interval=SLEEP_INTERVAL):
        self.wait_for_element_present_by_xpath(TABLE_SPINNER_NOT_DISPLAYED_XPATH,
                                               retries=retries,
                                               interval=interval)

    def get_all_checkboxes(self):
        return self.driver.find_elements_by_css_selector(self.CHECKBOX_CSS)

    def get_all_table_rows(self):
        return [elem.text.split('\n') for elem in
                self.driver.find_elements_by_css_selector(self.TABLE_ROWS_CSS) if elem.text]

    def get_all_tables_counters(self):
        counters = self.driver.find_elements_by_css_selector(self.TABLE_COUNTER)
        extracted_counters = []
        for counter in counters:
            extracted_counters.append(self.extract_first_int(counter.text))
        return extracted_counters

    def get_table_count(self):
        return int(self.driver.find_element_by_css_selector(self.TABLE_COUNTER).text[1:-1])

    def page_back(self):
        self.driver.back()

    def click_ok_button(self):
        self.click_button('OK')

    def safe_refresh(self):
        self.driver.get(self.driver.current_url)

    def wait_for_uploading_file(self, file_name):
        self.wait_for_element_present_by_text(file_name)

    @staticmethod
    def __upload_file_on_element(element, file_path):
        element.send_keys(file_path)

    def upload_file_on_element(self, element, file_content, is_bytes=False, prefix=None):
        if not prefix:
            prefix = TEMP_FILE_PREFIX
        else:
            prefix += TEMP_FILE_PREFIX
        with NamedTemporaryFile(delete=False, prefix=prefix) as temp_file:
            temp_file.write(file_content if is_bytes else bytes(file_content, 'utf-8'))
            temp_file.file.flush()
            Page.__upload_file_on_element(element, temp_file.name)
            fname = os.path.basename(temp_file.name)
            self.wait_for_uploading_file(fname)
            return fname

    def upload_file_by_id(self, input_id, file_content, is_bytes=False, prefix=None):
        element = self.wait_for_element_present_by_id(input_id)
        return self.upload_file_on_element(element, file_content, is_bytes, prefix)

    def close_dropdown(self):
        el = self.driver.find_element_by_css_selector(self.DROPDOWN_OVERLAY_CSS)
        ActionChains(self.driver).move_to_element_with_offset(el, 100, 100).click().perform()

    def click_tab(self, tab_title):
        self.driver.find_element_by_xpath(self.TAB_HEADER_XPATH.format(tab_title=tab_title)).click()

    def find_vertical_tabs(self):
        vertical_tabs = []
        for tab in self.driver.find_elements_by_css_selector(self.VERTICAL_TABS_CSS):
            if tab.text:
                vertical_tabs.append(tab.text)
        return vertical_tabs

    def get_vertical_tab_elements(self):
        return [tab for tab in self.driver.find_elements_by_css_selector(self.VERTICAL_TABS_CSS) if tab.text != '']

    def get_filename_by_input_id(self, input_id):
        return self.driver.find_element_by_xpath(
            f'//div[child::input[@id=\'{input_id}\']]/div[contains(@class, \'file-name\')]').text

    def is_saved_queries_opened(self):
        saved_queries = self.driver.find_elements_by_css_selector('button[title="Saved Queries"] > span')
        return any(elem.is_displayed() for elem in saved_queries)

    @staticmethod
    def is_element_disabled(element):
        return 'disabled' in element.get_attribute('class')

    def is_element_disabled_by_id(self, single_id):
        element = self.driver.find_element_by_id(single_id)
        return self.is_element_disabled(element)

    @staticmethod
    def is_input_error(input_element):
        return 'border-error' in input_element.get_attribute('class')

    def wait_for_modal_close(self):
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def fill_datepicker_date(self, date_to_fill):
        self.fill_text_field_by_css_selector(self.DATEPICKER_INPUT_CSS,
                                             normalize_timezone_date(date_to_fill.date().isoformat()))
        # Sleep through the time it takes the date picker to react to the filled date
        time.sleep(0.6)

    def close_datepicker(self):
        try:
            el = self.driver.find_element_by_css_selector(self.DATEPICKER_OVERLAY_CSS)
            ActionChains(self.driver).move_to_element_with_offset(el, 1, 1).click().perform()
            self.wait_for_element_absent_by_css(self.DATEPICKER_OVERLAY_CSS)
        except NoSuchElementException:
            # Already closed
            pass

    def click_remove_sign(self):
        self.click_button('X', partial_class=True, should_scroll_into_view=False)

    def clear_existing_date(self):
        self.click_remove_sign()
        # Make sure it is removed
        time.sleep(0.5)

    def find_existing_date(self):
        return self.wait_for_element_present_by_css('.md-datepicker .md-button.md-clear')

    def find_checkbox_by_label(self, text):
        return self.driver.find_element_by_xpath(self.CHECKBOX_XPATH_TEMPLATE.format(label_text=text))

    def find_checkbox_with_label_by_label(self, text):
        return self.driver.find_element_by_xpath(self.CHECKBOX_WITH_LABEL_XPATH.format(label_text=text))

    def find_field_by_label(self, text):
        return self.driver.find_element_by_xpath(self.FIELD_WITH_LABEL_XPATH.format(label_text=text))

    def find_checkbox_by_parent_id(self, parent_id):
        return self.driver.find_element_by_xpath(self.CHECKBOX_BY_PARENT_ID.format(parent_id=parent_id))

    def find_active_page_size(self):
        return self.driver.find_element_by_xpath(self.TABLE_PAGE_SIZE_ACTIVE_XPATH).text

    def click_row_checkbox(self, index=1):
        self.driver.find_element_by_css_selector(self.TABLE_ROW_CHECKBOX_CSS.format(child_index=index)).click()

    def click_table_checkbox(self):
        self.driver.find_element_by_css_selector(self.TABLE_ALL_CHECKBOX_CSS).click()

    def get_row_cell_text(self, row_index=1, cell_index=1):
        return self.driver.find_element_by_css_selector(
            self.TABLE_ROW_TEXT_CELL_CSS.format(row_index=row_index, cell_index=cell_index)).text

    def fill_enter_table_search(self, text):
        self.fill_text_field_by_css_selector(self.SEARCH_INPUT_CSS, text)
        self.key_down_enter(self.driver.find_element_by_css_selector(self.SEARCH_INPUT_CSS))

    def focus_on_element(self, elem_id):
        return self.driver.execute_script(f'document.querySelector("#{elem_id}").focus()')

    def blur_on_element(self, elem_id):
        return self.driver.execute_script(f'document.querySelector("#{elem_id}").blur()')

    def click_getting_started_overlay(self):
        self.wait_for_element_present_by_css('.md-overlay').click()
