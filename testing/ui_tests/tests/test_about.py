import json
import time

from ui_tests.tests.ui_test_base import TestBase
from axonius.consts.system_consts import METADATA_PATH, NODE_ID_ABSOLUTE_PATH
import testing.tests.conftest


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

    def _restart_gui(self):
        gui_service = self.axonius_system.gui
        gui_service.take_process_ownership()
        gui_service.stop(should_delete=False)
        gui_service.start_and_wait()
        time.sleep(5)
        testing.tests.conftest.axonius_set_test_passwords()
        self.login()

    def test_latest_version(self):
        # backup version string
        with open(METADATA_PATH, 'r') as metadata_file:
            metadata = json.load(metadata_file)
        version = metadata['Version']
        try:
            metadata['Version'] = '0_0_0'
            with open(METADATA_PATH, 'w') as metadata_file:
                json.dump(metadata, metadata_file)
            self._restart_gui()
            self.settings_page.switch_to_page()
            self.settings_page.click_about()
            self.settings_page.find_element_by_text('Latest Available Version')
        finally:
            # restore version metadata
            metadata['Version'] = version
            with open(METADATA_PATH, 'w') as metadata_file:
                json.dump(metadata, metadata_file)
            self._restart_gui()
