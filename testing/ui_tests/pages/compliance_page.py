import pytest
from selenium.common.exceptions import NoSuchElementException

from ui_tests.pages.page import Page


class CompliancePage(Page):
    ROOT_PAGE_CSS = 'li#compliance.x-nav-item'
    COMPLIANCE_TIP_CSS = '.x-compliance-tip'
    COMPLIANCE_PANEL_OPEN_CSS = '.v-navigation-drawer--open'
    TITLE_FAILED_CSS = 'div[title="Failed"]'
    TITLE_PASSED_CSS = 'div[title="Passed"]'
    SCORE_VALUE_CSS = 'span.score-value'

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
