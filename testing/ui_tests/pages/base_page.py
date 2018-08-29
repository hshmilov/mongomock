import time

from ui_tests.pages.page import Page


class BasePage(Page):
    DISCOVERY_RUN_ID = 'research_run'
    DISCOVERY_RUNNING_ID = 'discovery_running'

    @property
    def root_page_css(self):
        pass

    @property
    def url(self):
        pass

    def run_discovery(self):
        self.driver.find_element_by_id(self.DISCOVERY_RUN_ID).click()
        # Need to wait due to bug AX-1952
        time.sleep(60)
        self.wait_for_element_absent_by_id(self.DISCOVERY_RUNNING_ID, interval=60)
