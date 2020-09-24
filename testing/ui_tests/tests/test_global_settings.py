import os
import random
import shutil
import tarfile
from pathlib import Path
import pytest
import boto3
from botocore.exceptions import ClientError

from retrying import retry
from selenium.common.exceptions import NoSuchElementException

from scripts.instances.instances_consts import PROXY_DATA_HOST_PATH
from axonius.utils.json import to_json, from_json
from axonius.utils.wait import wait_until
from services.plugins.gui_service import GuiService
from services.standalone_services.smtp_service import SmtpService
from test_credentials.test_aws_credentials import (AWS_DEV_3_TESTING_BUCKET_RW_ACCESS_KEY_ID,
                                                   AWS_DEV_3_TESTING_BUCKET_RW_SECRET_ACCESS_KEY)
from test_credentials.test_gui_credentials import AXONIUS_USER
from test_credentials.test_ad_credentials import ad_client1_details
from test_credentials.json_file_credentials import client_details as json_file_creds
from test_helpers.log_tester import LogTester
from test_helpers.machines import PROXY_IP, PROXY_PORT
from ui_tests.tests.ui_consts import GUI_LOG_PATH, SYSTEM_SCHEDULER_LOG_PATH, AD_ADAPTER_NAME, JSON_ADAPTER_NAME,\
    S3_DEVICES_BACKUP_FILE_NAME, S3_USERS_BACKUP_FILE_NAME
from ui_tests.tests.ui_test_base import TestBase


INVALID_EMAIL_HOST = 'dada...$#@'
AXONIUS_CI_TESTS_BUCKET = 'axonius-testing'
AXONIUS_BACKUP_FILENAME = 'axonius_backup.tar.gz'
S3_BACKUP_FILE_PATTERN = 'Completed S3 backup file name: (.*)\\.gpg'
S3_FILES_LOCAL_DIRECTORY = 'tmp_backup_files'


class TestGlobalSettings(TestBase):

    s3_passphrase = None

    def test_email_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)

        # Invalid host is not being tested, an open bug
        # self.settings_page.fill_email_host(INVALID_EMAIL_HOST)

        self.settings_page.fill_email_port(-5)
        assert self.settings_page.get_email_port() == '5'

        # Ports above the maximum are also not validated
        # self.settings_page.fill_email_port(555)
        # self.settings_page.fill_email_port(88888)
        # self.settings_page.find_email_port_error()

    def test_email_host_validation(self):
        smtp_service = SmtpService()
        smtp_service.take_process_ownership()

        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)

        self.settings_page.fill_email_host(smtp_service.fqdn)
        self.settings_page.fill_email_port(smtp_service.port)

        self.settings_page.click_save_global_settings()
        self.settings_page.wait_email_connection_failure_toaster(smtp_service.fqdn)

        with smtp_service.contextmanager(retry_if_fail=True):
            self.settings_page.click_save_button()
            self.settings_page.wait_for_saved_successfully_toaster()

        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)
        self.settings_page.click_save_global_settings()

    def test_maintenance_endpoints(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.toggle_advanced_settings()
        gui_service = GuiService()

        assert gui_service.troubleshooting().strip() == b'true'
        toggle = self.settings_page.find_remote_support_toggle()
        assert self.settings_page.is_toggle_selected(toggle)

        self.settings_page.set_remote_support_toggle(make_yes=False)
        wait_until(lambda: gui_service.troubleshooting().strip() == b'false')

        self.settings_page.set_remote_support_toggle(make_yes=True)
        wait_until(lambda: gui_service.troubleshooting().strip() == b'true')

        assert gui_service.analytics().strip() == b'true'
        toggle = self.settings_page.find_analytics_toggle()
        assert self.settings_page.is_toggle_selected(toggle)

        self.settings_page.set_analytics_toggle(make_yes=False)
        wait_until(lambda: gui_service.analytics().strip() == b'false')

        self.settings_page.set_analytics_toggle(make_yes=True)
        wait_until(lambda: gui_service.analytics().strip() == b'true')

    def test_remote_access_log(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.toggle_advanced_settings()

        self.settings_page.set_provision_toggle(make_yes=False)
        self.settings_page.fill_remote_access_timeout('0.01')  # 36 seconds
        self.settings_page.click_start_remote_access()
        wait_until(
            lambda: LogTester(GUI_LOG_PATH).is_pattern_in_log(
                '(Creating a job for stopping the maintenance|Job already existing - updating its run time to)', 10))
        assert self.axonius_system.gui.provision().strip() == b'true'
        wait_until(lambda: self.axonius_system.gui.provision().strip() == b'false', total_timeout=60 * 1.5)

    def test_proxy_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()

        self.settings_page.set_proxy_settings_enabled()
        self.settings_page.fill_proxy_address(PROXY_IP)
        port = str(PROXY_PORT)
        self.settings_page.fill_proxy_port(port)
        self.settings_page.save_and_wait_for_toaster()

        @retry(wait_fixed=1000, stop_max_attempt_number=60 * 2)
        def proxy_settings_propagate():
            content = PROXY_DATA_HOST_PATH.read_text().strip()
            assert content == f'{{"creds": "{PROXY_IP}:{port}", "verify": true}}'

        proxy_settings_propagate()

    def test_bad_proxy_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()

        self.settings_page.set_proxy_settings_enabled()
        self.settings_page.fill_proxy_address('1.2.3.4')
        self.settings_page.fill_proxy_port('1234')
        self.settings_page.click_save_global_settings()
        self.settings_page.wait_for_toaster(self.settings_page.BAD_PROXY_TOASTER)

    def test_require_connection_label_setting(self):
        # save without connection label
        assert not self.settings_page.get_connection_label_required_value()
        self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.wait_for_data_collection_toaster_start()
        self.adapters_page.remove_server(ad_client1_details)

        # make connection label required
        self.settings_page.toggle_connection_label_required()
        self.settings_page.click_save_button()
        self.settings_page.wait_for_saved_successfully_toaster()
        assert self.settings_page.get_connection_label_required_value()

        # verify that save fails without connection label
        with pytest.raises(NoSuchElementException):
            self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.click_cancel()

        # verify that save succeeds with connection label
        ad_client1_details['connectionLabel'] = 'connection'
        self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.wait_for_data_collection_toaster_start()

        # clean up
        self.adapters_page.remove_server(ad_client1_details)
        self.settings_page.toggle_connection_label_required()
        self.settings_page.click_save_button()
        self.settings_page.wait_for_saved_successfully_toaster()
        assert not self.settings_page.get_connection_label_required_value()

    def test_save_button_enabled_again(self):
        """
        Test for checking that after user marked a certain checkbox for a certain settings group
        and then disabled the checkbox again, the save button gets enabled again.
        I.e, make sure validation checks are deactivated once the settings group isn't chosen
        - First step: Check that the save buttons behaves like it should for Amazon settings.
        - Second step: Check that if there was an existing error (including error message), and there
          is also an error from the Amazon settings, that after we un-check the amazon settings,
          the previous error (including error message) still appears.
          * In the middle also checks that after settings the bucket name for amazon
            that the save button is still disabled due to the previous error.
        """

        # First step
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()
        self.settings_page.set_amazon_settings_enabled()
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.fill_bucket_name('some value')
        assert not self.settings_page.is_save_button_disabled()
        self.settings_page.fill_bucket_name('')
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.set_amazon_settings_enabled(False)
        assert not self.settings_page.is_save_button_disabled()

        # Second step
        self.settings_page.set_correlation_schedule_settings_enabled()
        self.settings_page.fill_correlation_hours_interval(0)
        self.settings_page.key_down_tab()
        assert self.settings_page.find_correlation_hours_error()
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.set_amazon_settings_enabled()
        self.settings_page.fill_bucket_name('some value')
        assert self.settings_page.find_correlation_hours_error()
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.fill_bucket_name('')
        self.settings_page.set_amazon_settings_enabled(False)
        assert self.settings_page.find_correlation_hours_error()
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.set_correlation_schedule_settings_enabled(False)
        with pytest.raises(NoSuchElementException):
            self.settings_page.find_correlation_hours_error()
        assert not self.settings_page.is_save_button_disabled()

    @staticmethod
    def _generate_random_passphrase():
        return ''.join(str(random.randint(0, 9)) for _ in range(16))

    def _enable_s3_integration(self, passphrase):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()

        self.settings_page.set_s3_integration_settings_enabled()
        self.settings_page.fill_s3_bucket_name(AXONIUS_CI_TESTS_BUCKET)
        self.settings_page.fill_s3_access_key(AWS_DEV_3_TESTING_BUCKET_RW_ACCESS_KEY_ID)
        self.settings_page.fill_s3_secret_key(AWS_DEV_3_TESTING_BUCKET_RW_SECRET_ACCESS_KEY)
        self.settings_page.set_s3_backup_settings_enabled()
        self.settings_page.fill_s3_preshared_key(passphrase)
        self.settings_page.save_and_wait_for_toaster()

    def _disable_s3_integration(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()
        self.settings_page.set_s3_integration_settings_disabled()
        self.settings_page.save_and_wait_for_toaster()

    def test_s3_backup(self):
        local_dir = _get_backup_files_local_dir()
        self.s3_passphrase = self._generate_random_passphrase()
        self._enable_s3_integration(self.s3_passphrase)

        # Backup files will be added after discovery cycle is done.
        self.base_page.run_discovery()

        file_name = _get_s3_backup_file_name()

        if file_name:
            try:
                files = _get_s3_backup_file_content(file_name, local_dir, self.s3_passphrase)
                devices_file_name = files.get(S3_DEVICES_BACKUP_FILE_NAME, None)
                users_file_name = files.get(S3_USERS_BACKUP_FILE_NAME, None)

                def validate_data(db, internal_file_name):
                    if internal_file_name is not None:
                        with open(local_dir / internal_file_name, 'rt') as file:
                            items = from_json(file.read())
                            num_of_backup_items = len(items)

                        assert db.count_documents({}) == num_of_backup_items

                        if items is not None:
                            random_item_position = random.randint(0, num_of_backup_items - 1)
                            item_to_compare = items[random_item_position]
                            local_item = db.find_one({'internal_axon_id': item_to_compare['internal_axon_id']})

                            assert to_json(local_item, sort_keys=True) \
                                == to_json(item_to_compare, sort_keys=True)
                        else:
                            raise AssertionError(f'S3 Backup: backup file: {internal_file_name} is empty.')
                    else:
                        raise AssertionError('Unable to assert backup with empty file.')

                validate_data(self.axonius_system.get_devices_db(), devices_file_name)
                validate_data(self.axonius_system.get_users_db(), users_file_name)
            finally:
                self._disable_s3_integration()
                remove_s3_backup_file(file_name)
                shutil.rmtree(local_dir)
        else:
            raise AssertionError('Unable to locate s3 backup file name')

    def _toggle_root_master(self, toggle_value):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])

        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.toggle_root_master(toggle_value)
        self.settings_page.save_and_wait_for_toaster()

    def test_remove_auto_query(self):
        self.settings_page.disable_auto_querying()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        assert len(self.devices_page.get_all_data()) > 0
        self.adapters_page.select_query_filter(attribute=self.devices_page.FIELD_ADAPTER_CONNECTION_LABEL,
                                               operator='in',
                                               value='NOT_EXSITS')
        assert len(self.devices_page.get_all_data()) > 0
        self.devices_page.click_query_search_when_auto_query_disabled()
        self.users_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 0
        self.settings_page.enable_auto_querying()

    def test_s3_restore(self):
        local_dir = _get_backup_files_local_dir()
        self.s3_passphrase = self._generate_random_passphrase()
        self._enable_s3_integration(self.s3_passphrase)

        # Backup files will be added after discovery cycle is done.
        self.base_page.run_discovery()

        file_name = _get_s3_backup_file_name()

        if file_name:
            try:
                files = _get_s3_backup_file_content(file_name, local_dir, self.s3_passphrase)
                devices_file_name = files.get(S3_DEVICES_BACKUP_FILE_NAME, None)
                users_file_name = files.get(S3_USERS_BACKUP_FILE_NAME, None)

                # get devices and users data.
                def get_backup_data(internal_file_name):
                    if internal_file_name is not None:
                        with open(local_dir / internal_file_name, 'rt') as file:
                            items = from_json(file.read())
                            if items is not None:
                                num_of_backup_items = len(items)
                                random_item_position = random.randint(0, num_of_backup_items - 1)
                                item_to_compare = items[random_item_position]
                                return {
                                    'num_of_items': num_of_backup_items,
                                    'item_to_compare': item_to_compare
                                }
                            raise AssertionError(f'S3 Restore: backup file: {internal_file_name} is empty.')
                    else:
                        raise AssertionError('Unable to assert backup with empty file.')

                devices_data = get_backup_data(devices_file_name)
                users_data = get_backup_data(users_file_name)

                # Start restore process after backup data is ready for comparison.
                self._toggle_root_master(True)

                self._enable_s3_integration(self.s3_passphrase)

                # Clean adapters connection so only backup data will be inserted.
                self.adapters_page.clean_adapter_servers(AD_ADAPTER_NAME)
                self.adapters_page.clean_adapter_servers(JSON_ADAPTER_NAME)

                # Restore process is running at the beginning of a cycle.
                self.base_page.run_discovery()

                def assert_data_after_restore(db, item_to_compare, num_of_backup_items):
                    assert db.count_documents({}) == num_of_backup_items
                    local_item = db.find_one({'internal_axon_id': item_to_compare['internal_axon_id']})

                    for adapter_entity in (local_item.get('adapters') or []):
                        if adapter_entity.get('data'):
                            adapter_entity['data'].pop('backup_source', None)

                    local_item.pop('_id', None)
                    item_to_compare.pop('_id', None)
                    assert to_json(local_item, sort_keys=True) \
                        == to_json(item_to_compare, sort_keys=True)

                assert_data_after_restore(self.axonius_system.get_devices_db(), devices_data.get('item_to_compare'),
                                          devices_data.get('num_of_items'))
                assert_data_after_restore(self.axonius_system.get_users_db(), users_data.get('item_to_compare'),
                                          users_data.get('num_of_items'))

            finally:
                # Add adapters credentials for other tests.
                self._disable_s3_integration()
                self._toggle_root_master(False)
                self.adapters_page.add_server(ad_client1_details)
                self.adapters_page.add_server(json_file_creds, JSON_ADAPTER_NAME)
                remove_s3_backup_file(file_name)
                # Remove local dir
                shutil.rmtree(local_dir)

        else:
            raise AssertionError('Unable to locate s3 backup file name')


def _get_backup_files_local_dir():
    current_dir = Path().absolute()
    return current_dir / S3_FILES_LOCAL_DIRECTORY


def _get_s3_backup_file_name():
    # get latest backup file name
    wait_until(lambda: LogTester(SYSTEM_SCHEDULER_LOG_PATH).is_pattern_in_log(S3_BACKUP_FILE_PATTERN,
                                                                              10), 60 * 10)
    log_rows = LogTester(SYSTEM_SCHEDULER_LOG_PATH).get_pattern_lines_from_log(S3_BACKUP_FILE_PATTERN, 10)
    # e.g: log_rows =
    # ["Completed S3 backup file name: axonius_backup_Master_None__2020-04-21_08:31:25.524785.tar.gz.gpg"]
    return log_rows[len(log_rows) - 1].split(':', 1)[1].strip()


def _get_s3_backup_file_content(file_name, backup_local_directory, passphrase):
    Path(backup_local_directory).mkdir(parents=True, exist_ok=True)

    backup_local_file_path = backup_local_directory / file_name
    decrypted_backup_local_file = backup_local_directory / 'decrypted_backup.tar.gz'

    client = boto3.client(
        's3',
        aws_access_key_id=AWS_DEV_3_TESTING_BUCKET_RW_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_DEV_3_TESTING_BUCKET_RW_SECRET_ACCESS_KEY
    )

    print(file_name)
    client.download_file(AXONIUS_CI_TESTS_BUCKET, str(file_name), str(backup_local_file_path))

    os.system(f'echo {passphrase} | gpg --batch --yes --passphrase-fd 0 --output'
              f' {decrypted_backup_local_file}'
              f' --decrypt {backup_local_file_path}')

    devices_file_name = None
    users_file_name = None

    with tarfile.open(decrypted_backup_local_file, mode='r') as tar:
        tar.extractall(backup_local_directory)
        names = tar.getnames()
        for zipped_file_name in names:
            if zipped_file_name.startswith('devices'):
                devices_file_name = zipped_file_name
            elif zipped_file_name.startswith('users'):
                users_file_name = zipped_file_name

    return {
        'devices_file_name': devices_file_name,
        'users_file_name': users_file_name
    }


def remove_s3_backup_file(file_name):
    client = boto3.client(
        's3',
        aws_access_key_id=AWS_DEV_3_TESTING_BUCKET_RW_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_DEV_3_TESTING_BUCKET_RW_SECRET_ACCESS_KEY
    )

    try:
        client.delete_object(Bucket=AXONIUS_CI_TESTS_BUCKET, Key=file_name)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code != 'NotFound':
            raise e
