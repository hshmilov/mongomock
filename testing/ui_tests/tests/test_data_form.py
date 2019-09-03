from services.adapters.alertlogic_service import AlertlogicService
from alertlogic_adapter.consts import DEFAULT_DOMAIN
from ui_tests.tests.ui_test_base import TestBase


class TestDataForm(TestBase):

    ALERTLOGIC_PLUGIN_NAME = 'alertlogic_adapter'
    ALERTLOGIC_PLUGIN_TITLE = 'Alert Logic'

    def test_default_values(self):
        try:
            with AlertlogicService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(self.ALERTLOGIC_PLUGIN_TITLE)
                self.adapters_page.click_adapter(self.ALERTLOGIC_PLUGIN_TITLE)
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.fill_creds(apikey='rubbish')
                self.adapters_page.click_save()
                self.adapters_page.wait_for_element_present_by_text(DEFAULT_DOMAIN)
                self.adapters_page.wait_for_problem_connecting_to_server()
        finally:
            self.adapters_page.clean_adapter_servers(self.ALERTLOGIC_PLUGIN_TITLE)
            self.wait_for_adapter_down(self.ALERTLOGIC_PLUGIN_NAME)
