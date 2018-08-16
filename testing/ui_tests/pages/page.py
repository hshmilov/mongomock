import logging
import time
import urllib.parse

from selenium.common.exceptions import (ElementNotVisibleException,
                                        NoSuchElementException,
                                        StaleElementReferenceException,
                                        WebDriverException)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from services.axon_service import TimeoutException

logger = logging.getLogger(f'axonius.{__name__}')

# arguments[0] is the argument being passed by execute_script of selenium's driver
SCROLL_TO_TOP = '(function(container){container.scrollTo(0,0)})(arguments[0] || window)'
SCROLL_INTO_VIEW_JS = '''
var containerElement = arguments[1] || window;
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
BUTTON_DEFAULT_CLASS = 'x-btn'
BUTTON_TYPE_A = 'a'
TOASTER_CLASS_NAME = 'x-toast'
TOASTER_ELEMENT_WITH_TEXT_TEMPLATE = '//div[@class=\'x-toast\' and text()=\'{}\']'
RETRY_WAIT_FOR_ELEMENT = 150
SLEEP_INTERVAL = 0.2


class Page:
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

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
        logger.info(f'Switching to {self.root_page_css}')
        self.wait_for_element_present_by_css(self.root_page_css)
        self.driver.find_element_by_css_selector(self.root_page_css).click()

    def scroll_to_top(self):
        self.driver.execute_script('window.scrollTo(0, 0)')

    @staticmethod
    def clear_element(element):
        element.send_keys(Keys.LEFT_CONTROL, 'a')
        element.send_keys(Keys.BACKSPACE)

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
    def get_button_xpath(text, button_type=BUTTON_DEFAULT_TYPE, button_class=BUTTON_DEFAULT_CLASS):
        button_xpath_template = './/{}[@class=\'{}\' and .//text()=\'{}\']'
        xpath = button_xpath_template.format(button_type, button_class, text)
        return xpath

    def get_button(self, text, button_type=BUTTON_DEFAULT_TYPE, button_class=BUTTON_DEFAULT_CLASS, context=None):
        base = context if context is not None else self.driver
        xpath = self.get_button_xpath(text, button_type=button_type, button_class=button_class)
        return base.find_element_by_xpath(xpath)

    # this is a special case where the usual get_button doesn't work, name will be changed later
    def get_special_button(self, text):
        elems = self.driver.find_elements_by_css_selector('button.x-btn')
        for elem in elems:
            if elem.text == text:
                return elem
        return None

    def click_button(self,
                     text,
                     call_space=True,
                     button_type=BUTTON_DEFAULT_TYPE,
                     button_class=BUTTON_DEFAULT_CLASS,
                     ignore_exc=False,
                     with_confirmation=False,
                     context=None):
        button = self.get_button(text,
                                 button_type=button_type,
                                 button_class=button_class,
                                 context=context)
        self.scroll_into_view(button)
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

    def scroll_into_view(self, element, window=None):
        try:
            self.scroll_into_view_no_retry(element, window)
        except StaleElementReferenceException:
            logger.info(f'Failed to scroll down into element {element}. retrying...')
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
                time.sleep(interval)
            except NoSuchElementException:
                pass
        raise TimeoutException(f'Timeout while waiting for {value}')

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
                time.sleep(interval)
            except NoSuchElementException:
                pass
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
            logger.info(f'Failed to find element with text {text}. retrying...')

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
                time.sleep(interval)
            except NoSuchElementException:
                pass
        raise TimeoutException(f'Timeout while waiting for {text}')

    def click_toggle_button(self,
                            toggle,
                            make_yes=True,
                            ignore_exc=False,
                            scroll_to_toggle=True):
        is_selected = toggle.is_selected()

        if (make_yes and not is_selected) or (not make_yes and is_selected):
            try:
                if scroll_to_toggle:
                    self.scroll_into_view(toggle)
                toggle.click()
                return True
            except WebDriverException:
                if not ignore_exc:
                    raise

        assert toggle.is_selected() == make_yes
        return False

    def select_option(self,
                      dropdown_css_selector,
                      text_box_css_selector,
                      selected_option_css_selector,
                      choice):
        self.driver.find_element_by_css_selector(dropdown_css_selector).click()
        text_box = self.driver.find_element_by_css_selector(text_box_css_selector)
        self.send_keys(text_box, choice)
        self.driver.find_element_by_css_selector(selected_option_css_selector).click()

    def select_option_without_search(self,
                                     dropdown_css_selector,
                                     selected_options_css_selector,
                                     text):
        self.driver.find_element_by_css_selector(dropdown_css_selector).click()
        options = self.driver.find_elements_by_css_selector(selected_options_css_selector)
        for option in options:
            if option.text == text:
                option.click()
                return option
        return None
