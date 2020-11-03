import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PosixPath

import pymongo
from retrying import retry

from axonius.consts.gui_consts import ChartViews
from axonius.consts.instance_control_consts import HOSTNAME_FILE_PATH
from axonius.consts.plugin_consts import (JOB_FINISHED_AT,
                                          SYSTEM_SCHEDULER_PLUGIN_NAME,
                                          TRIGGERABLE_HISTORY)
from axonius.consts.system_consts import (CORTEX_PATH, LOGS_PATH_HOST,
                                          METADATA_PATH)
from axonius.utils.smb import SMBClient
from install import UPLOADED_FILES_PATH
from scripts.backup.axonius_restore import RESTORE_FOLDER, RESTORE_WORKING_PATH
from test_credentials.test_gui_credentials import AXONIUS_USER
from ui_tests.tests.ui_consts import DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME
from ui_tests.tests.ui_test_base import TestBase

BACKUP_UPLOADS_STATUS = 'backup_uploads_status'
BACKUP_FILE_NAME = 'backup_filename'
JOB_COMPLETED_SUCCESSFUL = 'Successful'
JOB_COMPLETED_STATE = 'job_completed_state'
JOB_NAME = 'job_name'
JOB_NAME_BACKUP = 'backup'
BACKUP_SKIPPED = 'Backup Skipped'
BACKUP_JOB_STARTED = 'started_at'
AUDIT_SYSTEM_RESTORE = 'audit.restore.restored'
RESTORE_SCRIPT_PATH = PosixPath(CORTEX_PATH) / 'devops/scripts/backup'
RESTORE_LOG_FILE_NAME = 'axonius_restore.log'
RESTORE_LOG_FILE_PATH = RESTORE_SCRIPT_PATH / RESTORE_LOG_FILE_NAME
HOSTNAME_CHANGED = Path(UPLOADED_FILES_PATH) / 'hostname_changed'


class BackupSettingsData:
    key = 'axonius_axonius_axonius'
    smb_ip = '192.168.20.3'
    smb_file_path = '/backups_dump'
    smb_share_name = 'nopass'
    smb_share_anonymous = f'/{smb_share_name}{smb_file_path}'


class BackupDataUserAccount:
    username = 'axon'
    password = 'axon'
    first_name = 'axon_first_name'
    last_name = 'axon_last_name'
    role = 'Viewer'


class BackupInstanceData:
    master_default_name = 'Master'
    master_backup_name = 'MasterOfPuppets'


class BackupDataDeviceSaveQuery:
    asset_exists_name = 'BK_SQ_ASSET_NAME_EXISTS'
    asset_exists_filter = '((specific_data.data.name == ({"$exists": true, "$ne": ""})))'


class BackupDataDashboardChart:
    space_name = 'backup'
    chart_title = 'BACKUP_TEST'
    chart_type = ChartViews.histogram
    chart_data_list = ['1', '0']
    devices_sq_name = BackupDataDeviceSaveQuery.asset_exists_name
    users_sq_name = 'Non-local users'


class BackupDataEnforcement:
    name = 'Backup_Enforcement'
    trigger_query = DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME


class RestoreMessages:
    VERSION_CHECK_FAILURE = ' backup version does not match installed version'
    DECRYPTION_FAILED = 'backup decryption failed'
    OUT_OF_SPACE = 'not enough free space to proceed with restore process'
    NEW_HOST_ALREADY_SIGNUP = ('A clean host is required (no previous sign-up) when restoring on'
                               ' a different host from the backup instance.')
    COMPLETED_SUCCESSFULLY = 'Restore completed successfully '


# pylint: disable=arguments-differ
class BackupRestoreTestBase(TestBase):

    def _setup_backup_feature_flag(self, enable=True, history_enable=True):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.toggle_backup_visible_feature_flag(toggle_value=enable)
        self.settings_page.toggle_backup_history_feature_flag(toggle_value=history_enable)
        self.settings_page.save_and_wait_for_toaster()

    def setup_method(self, method, enable_on_feature_flag=True):
        super().setup_method(method)
        if enable_on_feature_flag:
            self._setup_backup_feature_flag()
            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=self.username, password=self.password)

    def teardown_method(self, method):
        self.logger.info(f'starting backup and restore teardown_method {method.__name__}')
        backup_name = self._get_backup_file_from_db()
        if backup_name:
            self._clean_last_successful_backup_from_db()
            self._delete_backup_file_from_smb(backup_name)
        self.save_restore_log(method.__name__)
        # make sure no backup system config leftover
        try:
            self.settings_page.switch_to_page()
            self.settings_page.toggle_backup_enable(toggle_value=False)
        except Exception:
            self.logger.error('failed to disable backup system config')
        self._setup_backup_feature_flag(enable=False, history_enable=False)
        super().teardown_method(method)

    @staticmethod
    def _get_build_version() -> str:
        version = json.loads(Path(METADATA_PATH).read_text()).get('Version')
        return version if version else 'DEVELOP'

    def _setup_backup_to_smb_anonymous(self, include_history=True,
                                       include_users_and_devices=True,
                                       overwrite_previous_backups=True):
        self.settings_page.toggle_backup_enable(toggle_value=True)
        self.settings_page.toggle_backup_include_history(toggle_value=include_history)
        self.settings_page.toggle_backup_include_users_and_devices(toggle_value=include_users_and_devices)
        self.settings_page.toggle_backup_overwrite_previous_backups(overwrite_previous_backups)
        self.settings_page.toggle_backup_smb_setting(toggle_value=True)
        self.settings_page.fill_backup_encryption_key(BackupSettingsData.key)
        self.settings_page.fill_backup_smb_path(BackupSettingsData.smb_share_anonymous)
        self.settings_page.fill_backup_smb_ip(BackupSettingsData.smb_ip)
        self.settings_page.save_and_wait_for_toaster()

    @staticmethod
    def _get_smb_client_anonymous():
        return SMBClient(ip=BackupSettingsData.smb_ip,
                         share_name=BackupSettingsData.smb_share_anonymous,
                         username='', password='', use_nbns=False)

    @classmethod
    def _delete_backup_file_from_smb(cls, backup_file_name='', directory_path=BackupSettingsData.smb_file_path):
        client = cls._get_smb_client_anonymous()
        client.delete_files_from_smb(files=[backup_file_name],
                                     directory_path=directory_path)

    def _get_backup_file_from_db(self):
        last_successful_backup = self.axonius_system.db.get_collection(
            SYSTEM_SCHEDULER_PLUGIN_NAME, TRIGGERABLE_HISTORY).find_one(
                {
                    JOB_NAME: JOB_NAME_BACKUP,
                    JOB_COMPLETED_STATE: JOB_COMPLETED_SUCCESSFUL,
                    f'result.{BACKUP_UPLOADS_STATUS}': JOB_COMPLETED_SUCCESSFUL
                },
                {
                    'result': 1
                },
                sort=[(JOB_FINISHED_AT, pymongo.DESCENDING)])
        return last_successful_backup['result'][BACKUP_FILE_NAME] if last_successful_backup else None

    @retry(retry_on_result=lambda result: result is None,
           wait_fixed=1000 * 10,
           stop_max_delay=1000 * 60 * 15)
    def _wait_and_get_backup_file_from_db(self) -> str:
        return self._get_backup_file_from_db()

    def _clean_last_successful_backup_from_db(self):
        self.axonius_system.db.get_collection(
            SYSTEM_SCHEDULER_PLUGIN_NAME, TRIGGERABLE_HISTORY).delete_one({
                JOB_NAME: JOB_NAME_BACKUP,
                JOB_COMPLETED_STATE: JOB_COMPLETED_SUCCESSFUL,
                f'result.{BACKUP_UPLOADS_STATUS}': JOB_COMPLETED_SUCCESSFUL
            })

    def _is_last_backup_skipped(self) -> bool:
        last_skipped = self.axonius_system.db.get_collection(
            SYSTEM_SCHEDULER_PLUGIN_NAME, TRIGGERABLE_HISTORY).find_one({
                JOB_NAME: JOB_NAME_BACKUP,
                JOB_COMPLETED_STATE: JOB_COMPLETED_SUCCESSFUL,
                'result': BACKUP_SKIPPED
            }, {'result': 1}, sort=[(JOB_FINISHED_AT, pymongo.DESCENDING)])
        return bool(last_skipped)

    def _get_backup_job_start_time(self) -> datetime:
        last_successful_backup = self.axonius_system.db.get_collection(
            SYSTEM_SCHEDULER_PLUGIN_NAME, TRIGGERABLE_HISTORY).find_one({
                JOB_NAME: JOB_NAME_BACKUP,
                JOB_COMPLETED_STATE: JOB_COMPLETED_SUCCESSFUL,
                f'result.{BACKUP_UPLOADS_STATUS}': JOB_COMPLETED_SUCCESSFUL
            }, {BACKUP_JOB_STARTED: 1}, sort=[(JOB_FINISHED_AT, pymongo.DESCENDING)])
        if last_successful_backup:
            return last_successful_backup[BACKUP_JOB_STARTED]
        raise ValueError('missing backup job start timestamp')

    @staticmethod
    def verify_backup_file_exsits_in_smb(smb_client: SMBClient, backup_file_name):
        assert next((file for file in smb_client.list_files_on_smb() if backup_file_name == file), None)

    def verify_backup_creation_on_smb(self, file_create_time):
        # covert SMB time to UTC
        # SMB time is offset - aware
        # mongo time is offset - naive
        # convert both to offset - naive
        file_creation = datetime.fromtimestamp(file_create_time).astimezone(timezone.utc).replace(tzinfo=None)
        backup_start = self._get_backup_job_start_time().replace(tzinfo=None)
        assert file_creation > backup_start

    def verify_backup_filename_pattern(self, name: str, overwrite_previous_backup: bool):
        version = self._get_build_version()
        # hostname is a filemame in instance_control
        hostname = self.get_master_hostname()

        if overwrite_previous_backup:
            assert f'axonius_{version}_{hostname}_backup.gpg.tar' == name

        else:
            timestamp = datetime.utcnow().strftime('%Y%m%d')
            assert f'axonius_{version}_{hostname}_{timestamp}_backup.gpg.tar' == name

    #  - - - - - - - - - - - - - - - - -
    #           RESTORE
    # - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _run_restore_script(filename='', key='', skip_version_check=False, parse_error=False) -> str:
        script = RESTORE_SCRIPT_PATH / 'axonius_restore.sh'
        # required on none export builds ( GCP )
        script.chmod(0o755)
        run_cmd = str(script) + f' -f {filename} -p {key} -si'
        run_cmd = f'{run_cmd} -svc -ci' if skip_version_check else run_cmd

        cp = subprocess.run(
            ['/bin/sh', '-c', run_cmd],
            universal_newlines=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            timeout=3600

        )
        if parse_error:
            return cp.stdout.split('restore exit with error')[1]
        return cp.stdout

    def download_backup_file_from_smb(self, file_name):
        RESTORE_FOLDER.mkdir(exist_ok=True)
        smb_client = self._get_smb_client_anonymous()
        smb_client.download_files_from_smb(files=[file_name],
                                           directory_path=BackupSettingsData.smb_file_path,
                                           download_directory=RESTORE_FOLDER.as_posix())

    def start_system_restore(self, file_name, decrypt_key):
        """
        run restore script
        re-login to system
        verify successful restore audit message
        :param file_name: backup file name to restore
        :param decrypt_key: passphrase to decrypt backup
        """
        output = self._run_restore_script(filename=file_name,
                                          key=decrypt_key,
                                          skip_version_check=True)

        assert RestoreMessages.COMPLETED_SUCCESSFULLY in output

        # re login after service restart
        self.login()
        self.audit_page.switch_to_page()
        self.audit_page.verify_template_by_label_search(AUDIT_SYSTEM_RESTORE, filename=file_name)

    @staticmethod
    def verify_restore_failure_message(msg: RestoreMessages, cmd_output: str):
        assert msg in cmd_output
        # verify restore working dir deleted
        assert not RESTORE_WORKING_PATH.exists()

    def save_restore_log(self, test_id):
        try:
            restore_log_file = (Path(os.getcwd()) / RESTORE_LOG_FILE_NAME)
            if restore_log_file.exists():
                shutil.copyfile(restore_log_file, LOGS_PATH_HOST / f'{test_id}__{RESTORE_LOG_FILE_NAME}')
            else:
                self.logger.debug('restore log file not exists')
        except Exception:
            self.logger.exception('Error copy restore log file')

    def verify_dashboard_space_and_chart(self, space_name, chart_title, chart_data_list, chart_type):
        self.dashboard_page.switch_to_page()
        self.dashboard_page.click_space_by_name(space_name)
        card = self.dashboard_page.find_dashboard_card(chart_title)
        self.dashboard_page.edit_and_assert_chart(card, chart_data_list, chart_type=chart_type)

    def verify_enforcement(self, name, query):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.click_enforcement(name)
        self.enforcements_page.select_trigger()
        assert self.enforcements_page.get_selected_saved_view_name() == query

    @staticmethod
    def get_master_hostname():
        return subprocess.check_output(
            [
                'docker',
                'exec',
                'instance-control',
                'cat',
                str(HOSTNAME_FILE_PATH)
            ],
            timeout=60).decode('utf-8').strip('\n')
