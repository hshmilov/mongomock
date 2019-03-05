import logging
import os
import time
import urllib.parse
from tempfile import NamedTemporaryFile

from selenium.common.exceptions import (ElementNotVisibleException,
                                        NoSuchElementException,
                                        StaleElementReferenceException,
                                        WebDriverException)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

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
        container.scrollBy(0, 10);
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
X_BODY = '.x-body'
TOGGLE_CHECKED_CLASS = 'x-checkbox x-checked'
TOASTER_CLASS_NAME = 'x-toast'
TOASTER_ELEMENT_WITH_TEXT_TEMPLATE = '//div[@class=\'x-toast\' and text()=\'{}\']'
TABLE_SPINNER_NOT_DISPLAYED_XPATH = '//div[@class=\'v-spinner\' and @style=\'display: none;\']'
RETRY_WAIT_FOR_ELEMENT = 150
SLEEP_INTERVAL = 0.2


class Page:
    LOADING_SPINNER_CSS = '.v-spinner-bg'
    LOADING_SPINNER_CSS2 = '.v-spinner'
    CHECKBOX_XPATH_TEMPLATE = '//div[child::label[text()=\'{label_text}\']]/div[contains(@class, \'x-checkbox\')]'
    CHECKBOX_WITH_LABEL_XPATH = '//div[contains(@class, \'x-checkbox\') and child::label[text()=\'{label_text}\']]'
    CHECKBOX_CSS = 'div.x-checkbox-container'
    DIV_BY_LABEL_TEMPLATE = '//div[child::label[text()=\'{label_text}\']]'
    DROPDOWN_OVERLAY_CSS = '.x-dropdown-bg'
    MODAL_OVERLAY_CSS = '.modal-overlay'
    CANCEL_BUTTON = 'Cancel'
    SAVE_BUTTON = 'Save'
    OK_BUTTON = 'OK'
    REMOVE_BUTTON = 'Remove'
    DELETE_BUTTON = 'Delete'
    ACTIONS_BUTTON = 'Actions'
    CONFIRM_BUTTON = 'Confirm'
    VERTICAL_TABS_CSS = '.x-tabs.vertical .header .header-tab'
    NAMED_TAB_XPATH = '//div[@class=\'x-tabs\']/ul/li[contains(@class, "header-tab")]//div[text()=\'{tab_title}\']'
    TABLE_ROWS_CSS = 'tbody .x-row.clickable'
    TABLE_COUNTER = 'div.count'

    JSON_ADAPTER_NAME = 'JSON File'
    CUSTOM_ADAPTER_NAME = 'Custom Data'

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

    @staticmethod
    def extract_first_int(text):
        return [int(s) for s in text if s.isdigit()][0]

    def fill_text_field_by_element_id(self, element_id, value, context=None, last_field=False):
        return self.fill_text_field_by(By.ID, element_id, value, context, last_field=last_field)

    def fill_text_field_by_name(self, name, value, context=None):
        return self.fill_text_field_by(By.NAME, name, value, context)

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
            self.clear_element(element)
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
            except WebDriverException:
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

    def scroll_into_view(self, element, window=None):
        try:
            self.scroll_into_view_no_retry(element, window)
        except StaleElementReferenceException:
            logger.info(f'Failed to scroll down into element {element}')
            raise

    def scroll_into_view_no_retry(self, element, window=None):
        self.driver.execute_script(SCROLL_TO_TOP, window)
        result = self.driver.execute_script(SCROLL_INTO_VIEW_JS, element, window)
        assert result, 'Failed to scroll'

    def wait_for_element_present_by_css(self,
                                        css,
                                        element=None,
                                        retries=RETRY_WAIT_FOR_ELEMENT,
                                        interval=SLEEP_INTERVAL):
        return self.wait_for_element_present(By.CSS_SELECTOR, css, element, retries, interval)

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
                                 element=None,
                                 retries=RETRY_WAIT_FOR_ELEMENT,
                                 interval=SLEEP_INTERVAL):
        for _ in range(retries):
            try:
                element = self.find_element(by, value, element)
                if element:
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
                element = self.find_element(by, value, element)
                if not element:
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
        elems = self.driver.find_elements_by_class_name(TOASTER_CLASS_NAME)
        for elem in elems:
            if elem.text == text:
                return elem
        return None

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

    def find_elements_by_xpath(self, xpath, element=None):
        if not element:
            element = self.driver
        try:
            return element.find_elements(by=By.XPATH, value=xpath)
        except ElementNotVisibleException:
            logger.info(f'Failed to find element by xpath {xpath}')

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

    @staticmethod
    def is_toggle_selected(toggle):
        return toggle.get_attribute('class') == TOGGLE_CHECKED_CLASS

    def click_toggle_button(self,
                            toggle,
                            make_yes=True,
                            ignore_exc=False,
                            scroll_to_toggle=True):
        is_selected = self.is_toggle_selected(toggle)

        if (make_yes and not is_selected) or (not make_yes and is_selected):
            try:
                if scroll_to_toggle:
                    self.scroll_into_view(toggle, X_BODY)
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

    @staticmethod
    def key_down_enter(element):
        element.send_keys(Keys.ENTER)

    @staticmethod
    def key_down_arrow_down(element):
        element.send_keys(Keys.ARROW_DOWN)

    def wait_for_spinner_to_end(self):
        self.wait_for_element_absent_by_css(self.LOADING_SPINNER_CSS)
        self.wait_for_element_absent_by_css(self.LOADING_SPINNER_CSS2)

    def wait_for_table_to_load(self):
        self.wait_for_element_present_by_xpath(TABLE_SPINNER_NOT_DISPLAYED_XPATH)

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

    def page_back(self):
        self.driver.back()

    def click_ok_button(self):
        self.click_button('OK')

    def safe_refresh(self):
        self.driver.get(self.driver.current_url)

    @staticmethod
    def __upload_file_on_element(element, file_path):
        element.send_keys(file_path)
        time.sleep(2)  # AX-3475

    @staticmethod
    def upload_file_on_element(element, file_content):
        with NamedTemporaryFile(delete=False, prefix=TEMP_FILE_PREFIX) as temp_file:
            temp_file.write(bytes(file_content, 'ascii'))
            temp_file.file.flush()
            return Page.__upload_file_on_element(element, temp_file.name)

    def upload_file_by_id(self, input_id, file_content):
        element = self.driver.find_element_by_id(input_id)
        self.upload_file_on_element(element, file_content)

    def close_dropdown(self):
        self.driver.find_element_by_css_selector(self.DROPDOWN_OVERLAY_CSS).click()

    def click_tab(self, tab_title):
        self.find_element_by_text(tab_title).click()

    def find_vertical_tabs(self):
        vertical_tabs = []
        for tab in self.driver.find_elements_by_css_selector(self.VERTICAL_TABS_CSS):
            if tab.text:
                vertical_tabs.append(tab.text)
        return vertical_tabs

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
