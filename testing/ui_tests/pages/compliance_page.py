import time
import pytest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from ui_tests.pages.page import Page


class CompliancePage(Page):
    ROOT_PAGE_CSS = 'li#compliance.x-nav-item'
    COMPLIANCE_TIP_CSS = '.x-compliance-tip'
    COMPLIANCE_EXPIRY_MODAL_CSS = '#x-compliance-expire-modal'
    COMPLIANCE_PANEL_OPEN_CSS = '.v-navigation-drawer--open'
    TITLE_FAILED_CSS = 'div[title="Failed"]'
    TITLE_PASSED_CSS = 'div[title="Passed"]'
    SCORE_VALUE_CSS = 'span.score-value'
    ENFORCE_MENU_BUTTON = 'Enforce'
    ENFORCEMENTS_FEATURE_LOCK_TIP_CSS = '.x-enforcements-feature-lock-tip'
    ENFORCE_MENU_DROPDOWN_CSS = '.x-enforcement-menu'
    SCORE_RULES_MODAL_CSS = '.x-compliance-active-rules'

    RULES_FILTER_DROPDOWN_CSS = '.rules-filter .x-combobox'
    CATEGORIES_FILTER_DROPDOWN_CSS = '.categories-filter .x-combobox'
    ACCOUNTS_FILTER_DROPDOWN_CSS = '.accounts-filter .x-combobox'
    ACCOUNTS_FILTER_OPTIONS_CSS = '.v-select-list .v-list-item'

    FILTER_ROW_XPATH = '//div[contains(@class, \'v-select-list\')]//div[contains(@class, \'v-list\')]//' \
                       'div[contains(@class, \'v-list-item\')]//' \
                       'div[contains(@title,\'{filter_text}\')]'
    SCORE_RULES_EDIT_MENU_CSS = '.score-card .score-header .ant-btn'
    SCORE_RULES_EDIT_BUTTON_CSS = '#edit_score_settings'
    SCORE_RULES_ROWS_CSS = '.rules-selection .v-list-item'
    SCORE_RULES_SAVE_BUTTON_CSS = '.ant-modal-footer .ant-btn-primary'

    COMPLIANCE_TABLE_TOTAL_RULE_COUNT_CSS = '.table-title .count'
    ACCOUNT_FIELD = 'Results (Failed/Checked)'

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

    def assert_compliance_expiry_modal(self):
        assert self.driver.find_element_by_css_selector(self.COMPLIANCE_EXPIRY_MODAL_CSS)

    def assert_no_compliance_expiry_modal(self):
        with pytest.raises(NoSuchElementException):
            self.driver.find_element_by_css_selector(self.COMPLIANCE_EXPIRY_MODAL_CSS)

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

    def open_rule_filter_dropdown(self):
        self.driver.find_element_by_css_selector(self.RULES_FILTER_DROPDOWN_CSS).click()

    def open_category_filter_dropdown(self):
        self.driver.find_element_by_css_selector(self.CATEGORIES_FILTER_DROPDOWN_CSS).click()

    def open_accounts_filter_dropdown(self):
        self.driver.find_element_by_css_selector(self.ACCOUNTS_FILTER_DROPDOWN_CSS).click()

    def get_number_of_account_filter_options(self):
        return len(self.driver.find_elements_by_css_selector(self.ACCOUNTS_FILTER_OPTIONS_CSS)) - 1

    def get_all_accounts_options(self):
        return [item.text for item in self.driver.find_elements_by_css_selector(self.ACCOUNTS_FILTER_OPTIONS_CSS)]

    def toggle_filter(self, filter_text):
        self.driver.find_element_by_xpath(self.FILTER_ROW_XPATH.format(filter_text=filter_text)).click()
        self.wait_for_table_to_load()

    def get_all_rules(self):
        return self.get_all_table_rows_elements()

    def get_all_rules_results(self):
        return self.get_column_data_inline(self.ACCOUNT_FIELD)

    def get_total_rules_count(self):
        return self.get_table_count()

    def open_rules_dialog(self):
        self.driver.find_element_by_css_selector(self.SCORE_RULES_EDIT_MENU_CSS).click()
        time.sleep(0.2)
        self.driver.find_element_by_css_selector(self.SCORE_RULES_EDIT_BUTTON_CSS).click()
        time.sleep(0.5)  # wait for dialog to open

    def get_rules_dialog_modal(self):
        return self.driver.find_element_by_css_selector(self.SCORE_RULES_MODAL_CSS)

    def close_without_save_rules_dialog(self):
        modal = self.get_rules_dialog_modal()
        ActionChains(self.driver).move_to_element_with_offset(modal, -1, -1).click().perform()
        time.sleep(0.5)  # wait for enforce lock tip to close. (clicking outside the modal)

    def is_score_rules_modal_visible(self):
        return self.get_rules_dialog_modal().is_displayed()

    def get_score_rules_items(self):
        return self.find_elements_by_css(self.SCORE_RULES_ROWS_CSS)

    def toggle_exclude_rule(self, positions):
        rules = self.get_score_rules_items()
        for position in positions:
            rules[position].click()

    def save_score_rules(self):
        self.get_rules_dialog_modal().find_element_by_css_selector(self.SCORE_RULES_SAVE_BUTTON_CSS).click()
        time.sleep(0.5)  # wait for dialog to close
