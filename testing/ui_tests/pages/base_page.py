from ui_tests.pages.page import Page


class BasePage(Page):
    DISCOVERY_RUN_ID = 'run_research'
    DISCOVERY_STOP_ID = 'stop_research'

    @property
    def root_page_css(self):
        pass

    @property
    def url(self):
        pass

    def run_discovery(self):
        self.driver.find_element_by_id(self.DISCOVERY_RUN_ID).click()
        self.wait_for_element_present_by_id(self.DISCOVERY_STOP_ID, retries=600)
        self.wait_for_element_present_by_id(self.DISCOVERY_RUN_ID, retries=600)
