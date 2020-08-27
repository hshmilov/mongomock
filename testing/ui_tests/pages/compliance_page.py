import time
import pytest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from ui_tests.pages.page import Page


class CompliancePage(Page):
    ROOT_PAGE_CSS = 'li#compliance.x-nav-item'
    COMPLIANCE_TIP_CSS = '.x-compliance-tip'
    COMPLIANCE_EXPIRY_MODAL_CSS = '#x-compliance-expire-modal'
    COMPLIANCE_PANEL_OPEN_CSS = '.ant-drawer-open'
    TITLE_FAILED_CSS = 'div[title="Failed"]'
    TITLE_PASSED_CSS = 'div[title="Passed"]'
    SCORE_VALUE_CSS = 'span.score-value'
    ENFORCE_MENU_BUTTON = 'Enforce'
    ENFORCE_BY_MAIL_BUTTON_ID = 'cis_send_mail'
    ENFORCEMENTS_FEATURE_LOCK_TIP_CSS = '.x-enforcements-feature-lock-tip'
    ENFORCE_MENU_DROPDOWN_CSS = '.x-enforcement-menu'
    SCORE_RULES_MODAL_CSS = '.x-compliance-active-rules'

    RULES_FILTER_DROPDOWN_CSS = '.rules-filter .x-combobox'
    CATEGORIES_FILTER_DROPDOWN_CSS = '.categories-filter .x-combobox'
    ACCOUNTS_FILTER_DROPDOWN_CSS = '.accounts-filter .x-combobox'
    ACCOUNTS_FILTER_OPTIONS_CSS = '.v-select-list .v-list-item'
    FAILED_ONLY_FILTER_CSS = 'button[label=\'Failed only\']'
    AGGREGATED_VIEW_FILTER_CSS = 'button[label=\'Aggregated view\']'

    FILTER_ROW_XPATH = '//div[contains(@class, \'v-select-list\')]//div[contains(@class, \'v-list\')]//' \
                       'div[contains(@class, \'v-list-item\')]//' \
                       'div[contains(@title,\'{filter_text}\')]'
    SCORE_RULES_EDIT_MENU_CSS = '.score-card .score-header .ant-btn'
    SCORE_RULES_EDIT_BUTTON_CSS = '#edit_score_settings'
    SCORE_RULES_ROWS_CSS = '.rules-selection .v-list-item'
    SCORE_RULES_SAVE_BUTTON_CSS = '.ant-modal-footer .ant-btn-primary'
    CIS_SELECT_CSS = '.cis-select .dropdown-input .x-select-trigger'
    CIS_OPTION_XPATH = '//div[contains(@class, \'x-select-options\')]//div[contains(@title,\'{cis_title}\')]'

    COMPLIANCE_TABLE_TOTAL_RULE_COUNT_CSS = '.table-title .count'
    ACCOUNT_FIELD = 'Results (Failed/Checked)'
    AWS_DEFAULT_RULES_NUMBER = 43
    AZURE_DEFAULT_RULES_NUMBER = 76

    COMPLIANCE_MAIL_ENFORCE_MODAL_CSS = '.x-modal compliance_email_dialog'
    EMAIL_SUBJECT_ID = 'mailSubject'
    EMAIL_AWS_ADMINS_ID = 'accountAdmins'
    EMAIL_SEND_BUTTON_CSS = '.modal-footer .ant-btn-primary'

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

    def toggle_failed_rules(self):
        self.driver.find_element_by_css_selector(self.FAILED_ONLY_FILTER_CSS).click()
        self.wait_for_table_to_load()

    def toggle_aggregated_view(self):
        self.driver.find_element_by_css_selector(self.AGGREGATED_VIEW_FILTER_CSS).click()
        self.wait_for_table_to_load()

    def assert_default_number_of_rules(self):
        #  asserts the count, to the default number of rules currently defined in cac.
        return self.get_total_rules_count() == self.AWS_DEFAULT_RULES_NUMBER

    def assert_azure_default_number_of_rules(self):
        #  asserts the count, to the default number of rules currently defined in cac.
        return self.get_total_rules_count() == self.AZURE_DEFAULT_RULES_NUMBER

    def select_cis_by_title(self, title):
        self.driver.find_element_by_css_selector(self.CIS_SELECT_CSS).click()
        self.driver.find_element_by_xpath(self.CIS_OPTION_XPATH.format(cis_title=title)).click()
        self.wait_for_table_to_be_responsive()

    def open_email_dialog(self):
        self.click_enforce_menu()
        self.driver.find_element_by_id(self.ENFORCE_BY_MAIL_BUTTON_ID).click()
        self.wait_for_table_to_be_responsive()

    def wait_for_email_modal(self):
        self.wait_for_element_present_by_css(self.COMPLIANCE_MAIL_ENFORCE_MODAL_CSS)

    def fill_enforce_by_mail_form(self, name, recipient=None, body=None, send_to_admins=False):
        self.fill_text_field_by_element_id(self.EMAIL_SUBJECT_ID, name)
        if recipient:
            self.fill_text_field_by_css_selector('.md-input', recipient, context=self.find_field_by_label('Recipients'))
            elem = self.find_field_by_label('Recipients').find_element_by_css_selector('.md-input')
            self.key_down_enter(elem)
        if body:
            custom_message_element = self.driver.find_element_by_xpath(
                self.DIV_BY_LABEL_TEMPLATE.format(label_text='Custom message (up to 500 characters)')
            )
            self.fill_text_field_by_tag_name('textarea', body, context=custom_message_element)
            assert custom_message_element.find_element_by_tag_name('textarea').get_attribute('value') == body[:500]
        if send_to_admins:
            self.driver.find_element_by_id(self.EMAIL_AWS_ADMINS_ID).click()
        self.driver.find_element_by_css_selector(self.EMAIL_SEND_BUTTON_CSS).click()
        self.wait_for_spinner_to_end()
