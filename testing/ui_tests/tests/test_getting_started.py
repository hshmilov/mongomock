import os
import pytest

from test_helpers.log_tester import LogTester
from ui_tests.tests.ui_consts import (GUI_LOG_PATH,
                                      READ_ONLY_USERNAME,
                                      NEW_PASSWORD,
                                      FIRST_NAME,
                                      LAST_NAME)
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.pages import page
from ui_tests.pages.reports_page import ReportConfig
from axonius.consts.metric_consts import GettingStartedMetric
from axonius.consts.plugin_consts import GUI_PLUGIN_NAME
from services.adapters.gotoassist_service import GotoassistService
from services.axon_service import TimeoutException
from services.axonius_service import get_service
from test_credentials.test_gotoassist_credentials import client_details


class TestGettingStarted(TestBase):
    LOGGED_IN_MARKER_PATH = '/home/ubuntu/cortex/.axonius_settings/.logged_in'
    ENFORCEMENT_NAME = 'Test Milestone Completion'
    SAVED_QUERY = 'Getting Started Query'
    GOTOASSIST_NAME = 'RescueAssist'

    log_tester = LogTester(GUI_LOG_PATH)

    def setup_method(self, method):
        self.axonius_system = get_service()
        # This steps ensure signup process will run
        if os.path.exists(self.LOGGED_IN_MARKER_PATH):
            os.remove(self.LOGGED_IN_MARKER_PATH)
        self.axonius_system.db.get_collection(db_name=GUI_PLUGIN_NAME, collection_name='signup').drop()
        super().setup_method(method)

    def test_fab_exist_after_signup(self):
        """
        Test getting-started FAB exist in page after signup
        (should be enabled by default after signup)
        """
        self.login_page.logout()
        self.login()
        self.settings_page.switch_to_page()
        self.base_page.get_getting_started_fab()

    def test_open_close_panel(self):
        """
        Test clicking on the FAB is opening the panel & clicking outside of the panel's boundaries is closing it.
        """
        self.base_page.open_getting_started_panel()
        self.base_page.click_getting_started_overlay()

    def test_disabling_getting_started(self):
        """
        Expect the getting started FAB to disappear after feature is disabled.
        """
        self.settings_page.disable_getting_started_feature()
        with pytest.raises(TimeoutException):
            self.base_page.get_getting_started_fab()
            self.log_tester.is_pattern_in_log(GettingStartedMetric.FEATURE_ENABLED_SETTING)
        self.settings_page.enable_getting_started_feature()

    def test_milestones_completion(self):
        # make sure the feature is enabled
        self.settings_page.enable_getting_started_feature()

        # 1) connect 3rd adapter and check designated milestone has been completed
        self.adapters_page.switch_to_page()
        with GotoassistService().contextmanager(take_ownership=True):
            self.adapters_page.connect_adapter(
                adapter_name=self.GOTOASSIST_NAME,
                server_details=client_details)
            self.base_page.assert_milestone_completed(page.Milestones.connect_adapters.name)

        # 2) examine a device and check designated milestone has been completed
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.base_page.assert_milestone_completed(page.Milestones.examine_device.name)

        # assert completion logs written
        self.log_tester.is_pattern_in_log(GettingStartedMetric.COMPLETION_STATE)

        # 3) save a new query and check milestone has been completed
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_and_save(query_name=self.SAVED_QUERY,
                                              query_filter=self.devices_page.JSON_ADAPTER_FILTER)
        self.base_page.assert_milestone_completed(page.Milestones.query_saved.name)

        # 4) tag a device and check milestone has been completed
        self.devices_page.switch_to_page()
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row_checkbox()
        self.devices_page.open_tag_dialog()
        self.devices_page.create_save_tag(tag_text='getting started milestone')
        self.base_page.assert_milestone_completed(page.Milestones.device_tag.name)

        # 5) create & exec ES and check if milestone has been completed
        self.enforcements_page.switch_to_page()
        self.enforcements_page.create_basic_enforcement(enforcement_name=self.ENFORCEMENT_NAME,
                                                        enforcement_view=self.SAVED_QUERY,
                                                        save=True)
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_run_button()
        self.base_page.assert_milestone_completed(page.Milestones.enforcement_executed.name)

        # 6) create and save a new chart, and check if milestone has been completed
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card('Devices', 'OS: Type', 'Getting Started - Milestone')
        self.base_page.assert_milestone_completed(page.Milestones.dashboard_created.name)

        # 7) save a new report and check if milestone has been completed
        self.reports_page.create_report(ReportConfig(report_name='Getting started Milestone'))
        self.base_page.assert_milestone_completed(page.Milestones.report_generated.name)

        # Check if completion msg exist
        self.base_page.open_getting_started_panel()
        self.base_page.getting_started_completion()

    def test_getting_started_permissions(self):
        """
        Test a user without read-write permission to Settings resource
        is not able to see the Getting Started component.
        """

        # make sure the feature is enabled
        self.settings_page.enable_getting_started_feature()

        # create a new user without Getting Started permissions
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(READ_ONLY_USERNAME,
                                           NEW_PASSWORD,
                                           FIRST_NAME,
                                           LAST_NAME,
                                           self.settings_page.READ_ONLY_ROLE)

        # logout from admin account and login to the new user account
        self.login_page.logout()
        self.login_page.login(READ_ONLY_USERNAME, NEW_PASSWORD)

        # assert the Getting started FAB is missing
        with pytest.raises(TimeoutException):
            self.base_page.get_getting_started_fab()
