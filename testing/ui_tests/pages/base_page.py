import logging
from ui_tests.pages.page import Page

# will be 60*60*5*0.2 seconds
DISCOVERY_TIMEOUT = 60 * 60 * 5

logger = logging.getLogger(f'axonius.{__name__}')


class BasePage(Page):
    DISCOVERY_RUN_ID = 'run_research'
    DISCOVERY_STOP_ID = 'stop_research'

    @property
    def root_page_css(self):
        pass

    @property
    def url(self):
        pass

    def wait_for_stop_research(self):
        self.wait_for_element_present_by_id(self.DISCOVERY_STOP_ID, retries=DISCOVERY_TIMEOUT)

    def wait_for_run_research(self):
        self.wait_for_element_present_by_id(self.DISCOVERY_RUN_ID, retries=DISCOVERY_TIMEOUT)

    def run_discovery(self, wait=True):
        logger.info(f'Running discovery with wait={wait}')
        self.driver.find_element_by_id(self.DISCOVERY_RUN_ID).click()
        if wait:
            self.wait_for_stop_research()
            self.wait_for_run_research()
        logger.info('Done discovery cycle')

    def stop_discovery(self):
        stop_element = self.wait_for_element_present_by_id(self.DISCOVERY_STOP_ID, retries=DISCOVERY_TIMEOUT)
        stop_element.click()
        self.wait_for_element_present_by_id(self.DISCOVERY_RUN_ID, retries=DISCOVERY_TIMEOUT)
