import time
import pytest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from ui_tests.pages.page import Page


class CompliancePage(Page):
    ROOT_PAGE_CSS = 'li#compliance.x-nav-item'
    COMPLIANCE_TIP_CSS = '.x-compliance-tip'
    COMPLIANCE_PANEL_OPEN_CSS = '.v-navigation-drawer--open'
    TITLE_FAILED_CSS = 'div[title="Failed"]'
    TITLE_PASSED_CSS = 'div[title="Passed"]'
    SCORE_VALUE_CSS = 'span.score-value'
    ENFORCE_MENU_BUTTON = 'Enforce'
    ENFORCEMENTS_FEATURE_LOCK_TIP_CSS = '.x-enforcements-feature-lock-tip'
    ENFORCE_MENU_DROPDOWN_CSS = '.x-enforcement-menu'

    @property
    def url(self):
        return f'{self.base_url}/cloud_asset_compliance'

    @property
    def root_page_css(self):
        return self.ROOT_PAGE_CSS

    def assert_default_compliance_roles(self):
        assert len(self.get_all_table_rows()) == 43

    def assert_compliance_tip(self):
        assert self.driver.find_element_by_css_selector(self.COMPLIANCE_TIP_CSS)

    def assert_no_compliance_tip(self):
        with pytest.raises(NoSuchElementException):
            self.driver.find_element_by_css_selector(self.COMPLIANCE_TIP_CSS)

    def assert_compliance_panel_is_open(self):
        assert self.driver.find_element_by_css_selector(self.COMPLIANCE_PANEL_OPEN_CSS)

    def get_total_passed_rules(self):
        return len(self.driver.find_elements_by_css_selector(self.TITLE_PASSED_CSS))

    def get_total_failed_rules(self):
        return len(self.driver.find_elements_by_css_selector(self.TITLE_FAILED_CSS))

    def get_current_score_value(self):
        score_text = self.driver.find_element_by_css_selector(self.SCORE_VALUE_CSS).text
        return int(score_text.split('%')[0])

    def click_enforce_menu(self):
        self.click_button(self.ENFORCE_MENU_BUTTON)
        time.sleep(0.1)  # wait for enforce menu dropdown to close.

    def get_feature_lock_tip(self):
        return self.driver.find_element_by_css_selector(self.ENFORCEMENTS_FEATURE_LOCK_TIP_CSS)

    def close_feature_lock_tip(self):
        modal = self.get_feature_lock_tip()
        ActionChains(self.driver).move_to_element_with_offset(modal, -1, -1).click().perform()
        time.sleep(0.5)  # wait for enforce lock tip to close. (clicking outside the modal)

    def is_enforcement_lock_modal_visible(self):
        return self.wait_for_element_present_by_css(self.ENFORCEMENTS_FEATURE_LOCK_TIP_CSS).is_displayed()

    def is_enforcement_actions_menu_visible(self):
        return self.wait_for_element_present_by_css(self.ENFORCE_MENU_DROPDOWN_CSS).is_displayed()
