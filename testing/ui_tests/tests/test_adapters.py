import pytest

from ui_tests.tests.ui_test_base import TestBase

from services.adapters.gotoassist_service import GotoassistService

JSON_ADAPTER_SEARCH = 'json'
JSON_ADAPTER_TEXT_FROM_DESCRIPTION = 'formatted'
JSON_ADAPTER_NAME = 'JSON File'


class TestAdapters(TestBase):
    def test_search(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.search(JSON_ADAPTER_SEARCH)
        adapter_list = self.adapters_page.get_adapter_list()
        assert len(adapter_list) == 1
        assert adapter_list[0].name == JSON_ADAPTER_NAME

        self.adapters_page.search(JSON_ADAPTER_TEXT_FROM_DESCRIPTION)
        adapter_list = self.adapters_page.get_adapter_list()
        assert not len(adapter_list), 'Search should work only on adapter name'

    @pytest.mark.skip('Not Implemented Yet')
    def test_connectivity(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        with GotoassistService().contextmanager(take_ownership=True):
            self.adapters_page.safe_refresh()
            self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
