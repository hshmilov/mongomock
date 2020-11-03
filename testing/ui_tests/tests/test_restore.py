import subprocess

from axonius.entities import EntityType
from scripts.backup.axonius_restore import RESTORE_FOLDER
from ui_tests.tests.backup_test_base import (BackupSettingsData, BackupRestoreTestBase, RestoreMessages,
                                             BackupDataUserAccount, BackupInstanceData, BackupDataDashboardChart,
                                             BackupDataEnforcement, BackupDataDeviceSaveQuery)

from ui_tests.pages.reports_page import ReportFrequency, ReportConfig
from ui_tests.tests.ui_consts import EmailSettings

BACKUP_FAKE_BIG_SIZE_FILE_NAME = 'axonius_temp_10GB_backup.gpg.tar'
FAKE_BIG_BACKUP_FILE_PATH = RESTORE_FOLDER / BACKUP_FAKE_BIG_SIZE_FILE_NAME


class TestRestoreSanity(BackupRestoreTestBase):

    BACKUP_NAME_DIFFERENT_VERSION = 'axonius_backupv5_axonius_20200916_backup.gpg.tar'
    BACKUP_FOLDER_DIFFERENT_VERSION = 'backups_dump/ci_testing'

    BACKUP_REPORT = ReportConfig(
        report_name='BACKUP_REPORT',
        add_dashboard=False,
        queries=[{
            'entity': 'Devices',
            'name': BackupDataDeviceSaveQuery.asset_exists_name
        }],
        add_scheduling=True,
        email_subject='axonius backup test',
        emails=['test@axonius.com'],
        period=ReportFrequency.monthly
    )

    def _download_from_smb_different_version_backup(self):
        RESTORE_FOLDER.mkdir(exist_ok=True)
        if not (RESTORE_FOLDER / self.BACKUP_NAME_DIFFERENT_VERSION).exists():
            # download old version
            smb_client = self._get_smb_client_anonymous()
            smb_client.download_files_from_smb(files=[self.BACKUP_NAME_DIFFERENT_VERSION],
                                               directory_path=self.BACKUP_FOLDER_DIFFERENT_VERSION,
                                               download_directory=RESTORE_FOLDER.as_posix())

    def _verify_no_devices_after_restore_config_only(self):
        self.devices_page.switch_to_page()
        assert self.devices_page.count_entities() == 0

    def test_restore_failure_on_version_check_and_key(self):

        self._download_from_smb_different_version_backup()
        cmd_resp = self._run_restore_script(self.BACKUP_NAME_DIFFERENT_VERSION, BackupSettingsData.key,
                                            parse_error=True)

        self.verify_restore_failure_message(RestoreMessages.VERSION_CHECK_FAILURE, cmd_resp)
        # check decryption failure on invalid key
        cmd_resp = self._run_restore_script(filename=self.BACKUP_NAME_DIFFERENT_VERSION,
                                            key='INVALID_KEY',
                                            skip_version_check=True,
                                            parse_error=True)

        self.verify_restore_failure_message(RestoreMessages.DECRYPTION_FAILED, cmd_resp)

    def test_failed_on_missing_diskspace(self):
        # create 10GB fake backup file so free space check will failure during restore
        try:
            RESTORE_FOLDER.mkdir(exist_ok=True)
            # create 10G fake file
            subprocess.check_call(
                ['fallocate', '-l 10GB', str(FAKE_BIG_BACKUP_FILE_PATH.resolve())]
            )
            cmd_resp = self._run_restore_script(BACKUP_FAKE_BIG_SIZE_FILE_NAME, BackupSettingsData.key,
                                                parse_error=True)
            self.verify_restore_failure_message(RestoreMessages.OUT_OF_SPACE, cmd_resp)

        # although we dont like try/finally in test we do want to make sure 10GB file got deleted
        finally:
            if FAKE_BIG_BACKUP_FILE_PATH.exists():
                FAKE_BIG_BACKUP_FILE_PATH.unlink()

    def test_failed_when_signup_on_new_node(self):
        self._download_from_smb_different_version_backup()
        cmd_resp = self._run_restore_script(self.BACKUP_NAME_DIFFERENT_VERSION,
                                            BackupSettingsData.key,
                                            skip_version_check=True,
                                            parse_error=True)
        self.verify_restore_failure_message(RestoreMessages.NEW_HOST_ALREADY_SIGNUP, cmd_resp)

    def _configure_data_before_backup(self):
        """
        Global Setting : Email Server, User Account
        Instance : update name
        Add Devices saved query
        Dashboard : add space and chart
        Enforcement : creat new task
        Report : create new report

        """
        self.settings_page.add_email_server(EmailSettings.host, EmailSettings.port)
        self.settings_page.add_user(BackupDataUserAccount.username,
                                    BackupDataUserAccount.password,
                                    BackupDataUserAccount.first_name,
                                    BackupDataUserAccount.last_name,
                                    BackupDataUserAccount.role)
        self.instances_page.change_instance_name(BackupInstanceData.master_default_name,
                                                 BackupInstanceData.master_backup_name)

        self.devices_page.create_saved_query(BackupDataDeviceSaveQuery.asset_exists_filter,
                                             BackupDataDeviceSaveQuery.asset_exists_name)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_new_space(BackupDataDashboardChart.space_name)
        self.dashboard_page.add_comparison_card(
            [{'module': 'Devices', 'query': BackupDataDashboardChart.devices_sq_name},
             {'module': 'Users', 'query': BackupDataDashboardChart.users_sq_name}],
            BackupDataDashboardChart.chart_title
        )
        self.enforcements_page.switch_to_page()
        self.enforcements_page.create_deploying_enforcement(BackupDataEnforcement.name,
                                                            BackupDataEnforcement.trigger_query)
        self.reports_page.create_report(self.BACKUP_REPORT)

    def _verify_data_post_restore(self):
        """
        Global Setting : Email Server, User Account
        Instance : check name
        Add Devices check saved query
        Dashboard : check space and chart
        Enforcement : check task
        Report : check report
        """

        self.settings_page.verify_email_server_details(True, EmailSettings.host, EmailSettings.port)
        self.settings_page.verify_user_account(BackupDataUserAccount.username,
                                               BackupDataUserAccount.first_name,
                                               BackupDataUserAccount.last_name,
                                               BackupDataUserAccount.role)
        self.instances_page.verify_instance_name(BackupInstanceData.master_backup_name)
        self.devices_page.verify_saved_query_filter(BackupDataDeviceSaveQuery.asset_exists_name,
                                                    BackupDataDeviceSaveQuery.asset_exists_filter)
        self.verify_dashboard_space_and_chart(BackupDataDashboardChart.space_name,
                                              BackupDataDashboardChart.chart_title,
                                              BackupDataDashboardChart.chart_data_list,
                                              BackupDataDashboardChart.chart_type)
        self.verify_enforcement(BackupDataEnforcement.name, BackupDataEnforcement.trigger_query)
        self.reports_page.verify_report(self.BACKUP_REPORT)

    def test_restore_on_same_node(self):
        """
         test system backup without history an no users and devices data

        """
        self.settings_page.switch_to_page()
        # start with fetching devices and users
        self.base_page.run_discovery()
        # config backup to smb share
        self._setup_backup_to_smb_anonymous(include_users_and_devices=False,
                                            include_history=False,
                                            overwrite_previous_backups=False)

        # setup data to backup
        self._configure_data_before_backup()

        # run discovery with backup
        self.base_page.run_discovery()
        backup_name = self._wait_and_get_backup_file_from_db()
        self.download_backup_file_from_smb(backup_name)

        # lets make sure data will be restored and databases which are not like
        # aggregator devices and users tables are empty.
        self._clean_db()

        # make sure db is clean - analyze why flaky
        assert self.axonius_system.db.get_entity_db(EntityType.Devices).count_documents({}) == 0

        # restore
        self.logger.info(f'backup file name : {backup_name}')
        self.start_system_restore(backup_name, BackupSettingsData.key)
        self.save_restore_log(test_id='test_restore_on_same_node')

        # data verification post restore:
        self._verify_no_devices_after_restore_config_only()
        self._verify_data_post_restore()

        # cleanup
        self._delete_backup_file_from_smb(backup_name)
