import pytest
from axonius.consts.scheduler_consts import (BACKUP_SETTINGS,
                                             SCHEDULER_CONFIG_NAME,
                                             BackupSettings)
from axonius.modules.common import AxoniusCommon
from services.axon_service import TimeoutException
from ui_tests.pages.page import SLEEP_INTERVAL
from ui_tests.pages.settings_page import BackupSettingsLabels
from ui_tests.tests.backup_test_base import BackupRestoreTestBase


class TestBackupFeatureFlags(BackupRestoreTestBase):

    def setup_method(self, method, enable_on_feature_flag=False):
        super().setup_method(method, enable_on_feature_flag)

    def test_backup_settings_is_hidden(self):
        self.settings_page.switch_to_page()
        with pytest.raises(TimeoutException):
            self.settings_page.click_lifecycle_settings()
            self.settings_page.wait_for_element_present_by_text(BackupSettingsLabels.enable,
                                                                retries=2,
                                                                interval=SLEEP_INTERVAL)

    def test_backup_settings_history_hidden(self):
        self._setup_backup_feature_flag(enable=True, history_enable=False)
        with pytest.raises(TimeoutException):
            self.settings_page.click_lifecycle_settings()
            self.settings_page.wait_for_element_present_by_text(BackupSettingsLabels.include_history,
                                                                retries=2,
                                                                interval=SLEEP_INTERVAL)

    def test_backup_settings_scheduler_disable(self):
        """
        enable backup on feature flag
        enable backup setting and configure
        disable backup on feature flag
        verify backup disable on scheduler setting on DB
        """
        self._setup_backup_feature_flag(enable=True, history_enable=True)
        self.settings_page.click_lifecycle_settings()
        self._setup_backup_to_smb_anonymous()
        self._setup_backup_feature_flag(enable=False, history_enable=False)

        assert not (AxoniusCommon().plugins.system_scheduler.
                    configurable_configs[SCHEDULER_CONFIG_NAME][BACKUP_SETTINGS][BackupSettings.enabled])
