import logging
import time
from services.axon_service import TimeoutException

from ui_tests.pages.entities_page import EntitiesPage
logger = logging.getLogger(f'axonius.{__name__}')


class QueriesPage(EntitiesPage):
    QUERY_ROW_BY_NAME_XPATH = '//tr[child::td[.//text()=\'{query_name}\']]'
    QUERY_NAME_BY_PART_XPATH = '//div[contains(text(), \'{query_name_part}\')]'
    CSS_SELECTOR_PANEL_ACTION_BY_NAME = '.saved-query-panel .actions .action-{action_name}'
    CSS_SELECTOR_CLOSE_PANEL_ACTION = '.actions .action-close'
    SAFEGUARD_REMOVE_BUTTON_SINGLE = 'Remove Saved Query'
    SAFEGUARD_REMOVE_BUTTON_MULTI = 'Remove Saved Queries'
    RUN_QUERY_BUTTON_TEXT = 'Run Query'
    NO_EXPRESSIONS_DEFINED_MSG = 'No query defined'
    EXPRESSION_UNSUPPORTED_MSG = 'Query not supported for the existing data'

    @property
    def url(self):
        raise NotImplementedError

    @property
    def root_page_css(self):
        raise NotImplementedError

    @property
    def parent_root_page_css(self):
        raise NotImplementedError

    def switch_to_page(self):
        logger.info(f'Switching to {self.parent_root_page_css}')
        self.wait_for_element_present_by_css(self.parent_root_page_css)
        self.driver.find_element_by_css_selector(self.parent_root_page_css).click()
        logger.info(f'Finished switching to {self.parent_root_page_css}')
        self.wait_for_table_to_load()
        self.click_button('Saved Queries', partial_class=True)

    def run_query(self):
        self.wait_for_element_present_by_css('.saved-query-panel')
        # wait for drawer animation end
        time.sleep(2)
        self.click_button(text=self.RUN_QUERY_BUTTON_TEXT)

    def find_query_row_by_name(self, query_name):
        return self.driver.find_element_by_xpath(self.QUERY_ROW_BY_NAME_XPATH.format(query_name=query_name))

    def click_query_row_by_name(self, query_name):
        self.find_query_row_by_name(query_name).click()

    def check_query_by_name(self, query_name):
        row = self.find_query_row_by_name(query_name)
        row.find_element_by_css_selector(self.CHECKBOX_CSS).click()

    def remove_selected_queries(self, confirm=False):
        if confirm:
            self.remove_selected_with_safeguard(self.SAFEGUARD_REMOVE_BUTTON_SINGLE, self.SAFEGUARD_REMOVE_BUTTON_MULTI)
        else:
            self.remove_selected_with_safeguard()

    def enforce_selected_query(self):
        self.wait_for_element_present_by_css('.saved-query-panel')
        # wait for drawer animation end
        time.sleep(2)
        self.get_enforce_panel_action().click()

    def find_query_name_by_part(self, query_name_part):
        return self.find_elements_by_xpath(self.QUERY_NAME_BY_PART_XPATH.format(query_name_part=query_name_part))

    def _find_panel_action_by_name(self, action_name):
        return self.wait_for_element_present_by_css(self.CSS_SELECTOR_PANEL_ACTION_BY_NAME
                                                    .format(action_name=action_name))

    def get_enforce_panel_action(self):
        return self._find_panel_action_by_name(action_name='enforce')

    def get_remove_panel_action(self):
        return self._find_panel_action_by_name(action_name='remove')

    def get_edit_panel_action(self):
        return self._find_panel_action_by_name(action_name='edit')

    def close_saved_query_panel(self):
        close_btn = self.wait_for_element_present_by_css(self.CSS_SELECTOR_CLOSE_PANEL_ACTION)
        close_btn.click()

    def get_query_description_from_panel(self):
        return self.wait_for_element_present_by_css('.x-side-panel .description p').text

    def get_query_name_from_panel(self):
        return self.wait_for_element_present_by_css('.x-side-panel__header .title').text

    def get_query_update_user_from_panel(self):
        return self.wait_for_element_present_by_css('.x-side-panel .updater div').text

    def get_query_last_update_from_panel(self):
        return self.wait_for_element_present_by_css('.x-side-panel .update div').text

    def get_query_expression_eval_message(self):
        """
        The panel has functionality for expressions evaluation:
        1) the expressions is valid and can be visualized
        2) the query is expressions is valid but empty
        3) the query expression contains missing data (not valid)
        :return:
        1 ) empty string
        2 ) No query defined
        3 ) Query not supported for the existing data
        """
        evaluation_result = ''
        try:
            self.wait_for_element_present_by_css('.x-side-panel .expression .x-filter')
        except TimeoutException:
            evaluation_result = self.wait_for_element_present_by_css('.x-side-panel .expression span').text

        return evaluation_result
