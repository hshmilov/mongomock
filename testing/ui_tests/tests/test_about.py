import json

from ui_tests.tests.ui_test_base import TestBase
from axonius_system import METADATA_PATH


class TestAbout(TestBase):
    def test_about(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_about()
        with open(METADATA_PATH, 'r') as metadata_file:
            metadata = json.load(metadata_file)
        for key, value in metadata.items():
            assert self.settings_page.find_element_by_text(key)
            assert self.settings_page.find_element_by_text(value)
