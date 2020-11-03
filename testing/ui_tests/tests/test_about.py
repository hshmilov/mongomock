import json
import time
from datetime import timedelta

from test_credentials.test_gui_credentials import AXONIUS_USER
from test_helpers.utils import get_server_date, get_datetime_format_by_gui_date
from ui_tests.tests.ui_test_base import TestBase
from axonius.consts.system_consts import METADATA_PATH, NODE_ID_ABSOLUTE_PATH


class TestAbout(TestBase):

    def _restart_gui(self):
        self.login_page.logout()
        gui_service = self.axonius_system.gui
        gui_service.take_process_ownership()
        gui_service.stop(should_delete=False)
        gui_service.start_and_wait()
        time.sleep(5)
        self.login()

    def _reset_to_trial_contract(self, days_remaining=60):
        self.login_page.logout()
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.clear_contract_datepicker()
        self.settings_page.fill_trial_expiration_by_remainder(days_remaining)

    def test_about(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        display_date_format = self.settings_page.get_date_format()

        self.settings_page.click_about()
        with open(METADATA_PATH, 'r') as metadata_file:
            metadata = json.load(metadata_file)
        if 'Commit Hash' in metadata:
            del metadata['Commit Hash']
        if 'Commit Date' in metadata:
            del metadata['Commit Date']
        metadata['Installed Version'] = metadata.pop('Version', None)
        with open(NODE_ID_ABSOLUTE_PATH, 'r') as node_id_file:
            metadata['Customer ID'] = node_id_file.read()

        self.settings_page.assert_about_tab_values(metadata.items(), display_date_format)

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

    def test_contract_expiry_date(self):
        server_date = get_server_date()
        expected_date = server_date + timedelta(self.settings_page.NEXT_DAYS_COUNT)

        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        default_date_format = self.settings_page.GUI_SETTINGS_DEFAULT_TIME_FORMAT

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()

        self.settings_page.click_feature_flags()
        self.settings_page.fill_contract_expiration_by_remainder(self.settings_page.NEXT_DAYS_COUNT, server_date)
        self.settings_page.save_and_wait_for_toaster()
        self._restart_gui()

        self.settings_page.switch_to_page()
        self.settings_page.click_about()
        self.settings_page.about_page_get_label_text(self.settings_page.ABOUT_PAGE_CONTRACT_EXPIRY_DATE_LABEL)
        assert self.settings_page.about_page_contract_details_exists()
        assert str(expected_date.date()) == self.settings_page\
            .about_page_get_label_value_by_key(self.settings_page.ABOUT_PAGE_CONTRACT_EXPIRY_DATE_LABEL)

        try:
            self.settings_page.click_gui_settings()
            self.settings_page.set_date_format(self.settings_page.GUI_SETTINGS_US_TIME_FORMAT)
            self.settings_page.save_and_wait_for_toaster()

            self.settings_page.click_about()
            visible_exp_date = self.settings_page.about_page_get_label_value_by_key(
                self.settings_page.ABOUT_PAGE_CONTRACT_EXPIRY_DATE_LABEL)
            assert visible_exp_date == expected_date.strftime(get_datetime_format_by_gui_date(
                self.settings_page.GUI_SETTINGS_US_TIME_FORMAT))
        # pylint: disable=try-except-raise
        except Exception:
            raise
        finally:
            self.settings_page.click_gui_settings()
            self.settings_page.set_date_format(default_date_format)
            self.settings_page.save_and_wait_for_toaster()

            self._reset_to_trial_contract()
            self.settings_page.save_and_wait_for_toaster()

    def test_missing_contract_expiry_date(self):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()

        self._reset_to_trial_contract()
        self.settings_page.save_and_wait_for_toaster()
        self._restart_gui()

        self.settings_page.switch_to_page()
        self.settings_page.click_about()
        assert not self.settings_page.about_page_contract_details_exists()
