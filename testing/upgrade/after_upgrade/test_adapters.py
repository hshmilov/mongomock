from ui_tests.tests.ui_test_base import TestBase


class TestAdapters(TestBase):
    def test_no_bad_adapters(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()

        for key in ('json', 'stress', 'qcore', 'traiana'):
            self.adapters_page.search(key)
            adapter_list = self.adapters_page.get_adapter_list()
            assert len(adapter_list) == 0

    def test_no_adapter_without_description(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        # if there is an adapter without description, it will fail
        self.adapters_page.get_adapter_list()
