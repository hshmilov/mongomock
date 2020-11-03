from datetime import datetime

from axonius.utils.wait import wait_until
from ui_tests.tests.backup_test_base import BackupSettingsData, BackupRestoreTestBase


class TestBackupSanity(BackupRestoreTestBase):

    def test_backup_settings_validation(self):
        """
        check setting page save button disable if missing mandatory params
        - check encryption ket size
        - check selected external repo
        - check history must include user and data
        """
        self.settings_page.switch_to_page()
        self.settings_page.toggle_backup_enable(toggle_value=True)
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.fill_backup_encryption_key('short_key')
        self.settings_page.find_backup_no_repo_selected_error()
        self.settings_page.toggle_backup_smb_setting(toggle_value=True)
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.fill_backup_smb_ip('1.1.1.1')
        self.settings_page.fill_backup_smb_path('/no/access')
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.fill_backup_encryption_key('short_key')
        assert self.settings_page.find_backup_invalid_encryption_key()
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.toggle_backup_include_users_and_devices(toggle_value=False)
        self.settings_page.toggle_backup_include_history(toggle_value=True)
        assert self.settings_page.is_save_button_disabled()
        assert self.settings_page.find_backup_missing_devices_and_user()

    def test_backup_config_only_to_smb(self):
        self.settings_page.switch_to_page()

        self._setup_backup_to_smb_anonymous(include_users_and_devices=False,
                                            include_history=False,
                                            overwrite_previous_backups=False)
        self.base_page.run_discovery()
        backup_file_name = self._wait_and_get_backup_file_from_db()
        smb_client = self._get_smb_client_anonymous()
        smb_shared_obj = smb_client.get_smb_file_attributes(
            path=f'{BackupSettingsData.smb_file_path}/{backup_file_name}')
        # check file is not zero size
        assert smb_shared_obj.file_size > 0
        # check file creation time
        self.verify_backup_creation_on_smb(smb_shared_obj.last_attr_change_time)
        # cleanup
        self.verify_backup_filename_pattern(name=backup_file_name, overwrite_previous_backup=False)

    def test_minimum_days_between_backup(self):
        self.settings_page.switch_to_page()
        self._setup_backup_to_smb_anonymous()
        self.base_page.run_discovery()
        backup_file_name = self._wait_and_get_backup_file_from_db()
        smb_client = self._get_smb_client_anonymous()
        self.verify_backup_file_exsits_in_smb(smb_client, backup_file_name)
        smb_shared_obj = smb_client.get_smb_file_attributes(
            path=f'{BackupSettingsData.smb_file_path}/{backup_file_name}')
        self.verify_backup_creation_on_smb(smb_shared_obj.last_attr_change_time)
        self.verify_backup_filename_pattern(name=backup_file_name, overwrite_previous_backup=True)
        # check - next backup will be skipped as min time between backup is 1 day
        self.base_page.run_discovery()
        wait_until(self._is_last_backup_skipped, total_timeout=60 * 5)

    def test_override_previous_backups_smb(self):
        self.settings_page.switch_to_page()
        self._setup_backup_to_smb_anonymous()

        start_discovery = datetime.now()
        self.base_page.run_discovery()
        backup_file_name = self._wait_and_get_backup_file_from_db()
        smb_client = self._get_smb_client_anonymous()
        self.verify_backup_file_exsits_in_smb(smb_client, backup_file_name)

        # check - backup type overwrite last build ( no timestamp in filename )
        self._clean_last_successful_backup_from_db()
        self.base_page.run_discovery()
        overwrite_backup_file_name = self._wait_and_get_backup_file_from_db()
        assert overwrite_backup_file_name == backup_file_name

        smb_shared_obj = smb_client.get_smb_file_attributes(
            path=f'{BackupSettingsData.smb_file_path}/{backup_file_name}')
        file_creation = datetime.fromtimestamp(smb_shared_obj.create_time)
        overwrite_file_last_changed = datetime.fromtimestamp(smb_shared_obj.last_attr_change_time)
        assert overwrite_file_last_changed > file_creation
