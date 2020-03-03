import json

from ui_tests.tests.ui_test_base import TestBase
from axonius.consts.system_consts import METADATA_PATH, NODE_ID_ABSOLUTE_PATH


class TestAbout(TestBase):
    def test_about(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_about()
        with open(METADATA_PATH, 'r') as metadata_file:
            metadata = json.load(metadata_file)
        if 'Commit Hash' in metadata:
            del metadata['Commit Hash']
        if 'Commit Date' in metadata:
            del metadata['Commit Date']
        with open(NODE_ID_ABSOLUTE_PATH, 'r') as node_id_file:
            metadata['Customer ID'] = node_id_file.read()
        for key, value in metadata.items():
            assert self.settings_page.find_element_by_text(key)
            assert self.settings_page.find_element_by_text(value)
