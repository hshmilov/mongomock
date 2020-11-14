import concurrent
import logging
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import zipfile
from io import BytesIO
from json import loads
from datetime import datetime, timedelta
from enum import Enum
from tempfile import NamedTemporaryFile

import pymongo

from axonius.clients.azure.utils import AzureBlobStorageClient, AzureBlobContainer, AzureBlob
from axonius.consts.plugin_consts import (AXONIUS_BACKUP_PATH, JOB_FINISHED_AT, SYSTEM_SCHEDULER_PLUGIN_NAME,
                                          CORE_UNIQUE_NAME, AXONIUS_SETTINGS_PATH, METADATA_PATH, TRIGGERABLE_HISTORY,
                                          NODE_ID, BYTES_TO_GB, BYTES_TO_MB)
from axonius.consts.scheduler_consts import BackupSettings, BackupRepoAzure, BackupRepoAws, BackupRepoSmb
from axonius.db.db_client import DB_PASSWORD, DB_USER, get_db_client, DB_HOST
from axonius.plugin_base import PluginBase
from axonius.utils.host_utils import get_free_disk_space
from axonius.utils.mongo_administration import get_collection_storage_size, get_database_data_size
from axonius.logging.audit_helper import (AuditCategory, AuditAction, AuditType)
from axonius.utils.smb import SMBClient
from axonius.clients.aws.utils import upload_file_to_s3, delete_file_from_s3
# pylint: disable=useless-super-delegation

GPG_CIPHER = 'AES256'
AVG_COMPRESSION_RATIO = 1

BACKUP_UPLOADS_STATUS = 'backup_uploads_status'
BACKUP_FILE_NAME = 'backup_filename'
SUCCESSFUL = 'Successful'
FAILURE = 'Failure'
SKIPPED = 'Backup Skipped'
SKIPPED_OUT_OF_SPACE = f'{SKIPPED} local host out of space'
BACKUP_TIMEOUT_12H = 60 * 60 * 12


class ExternalRepoType(Enum):
    SMB = 'SMB Share'
    AWS = 'AWS S3 Storage'
    AZURE = 'Azure Storage'


logger = logging.getLogger(f'axonius.{__name__}')


class BackupException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


def get_mongo_space_documents_size(include_history=False, include_devices_users_data=True) -> float:
    """
    :param include_history:
    :param include_devices_users_data:
    :return: size in GB
    """
    db_client = get_db_client()
    dbs = db_client.list_database_names()
    dbs_to_filter = ['aggregator', 'local']

    size_of_databases_without_aggregator = sum([
        get_database_data_size(db_client.get_database(db_name)) for db_name in dbs if db_name not in dbs_to_filter
    ])

    aggragator_collections_to_backup = list(
        filter(lambda col: aggregator_collection_filter(col, include_history, include_devices_users_data),
               db_client.aggregator.list_collection_names())
    )

    aggregator_size = sum(get_collection_storage_size(db_client.aggregator.get_collection(col_name))
                          for col_name in aggragator_collections_to_backup)

    return (aggregator_size / BYTES_TO_GB) + size_of_databases_without_aggregator


def aggregator_collection_filter(col_name='', include_history=False, include_devices_users_data=True) -> bool:
    """
    aggregator collections filter  - for a given collection name return true if required by backup configuration
     - includeHistory require that   - includeUsersAndDevices is true

    :param col_name: collection name from aggregator
    :param include_history:
    :param include_devices_users_data:
    :return: boolean
    """

    users_and_devices_collections = ['devices_db', 'users_db', 'users_fields', 'devices_fields',
                                     'device_adapters_raw_db', 'user_adapters_raw_db']

    if col_name in users_and_devices_collections:
        return include_devices_users_data
    if re.match(r'^historical.*db_view$', col_name) or re.match(r'_db_view$', col_name):
        return include_devices_users_data and include_history
    return 'historical' not in col_name


# pylint: disable=E1101,no-member
class BackupManager:
    # pylint: disable=R0902
    def __init__(self, config: dict):
        # load backup setting as they may changed since job put in queue
        self.db_user = DB_USER
        self.db_pass = DB_PASSWORD
        self.db_host = DB_HOST

        self.db_client = get_db_client()
        self.pluginbase_instance = PluginBase.Instance
        self._set_master_hostname()

        self.cipher_algo = GPG_CIPHER

        self.include_devices_users_data = config.get(BackupSettings.include_devices_users_data, True)
        self.include_history = config.get(BackupSettings.include_history, False)
        self.override_previous_backups = config.get(BackupSettings.override_previous_backups, False)
        self.min_days_between_cycles = config.get(BackupSettings.min_days_between_cycles, 1)
        self.pre_shared_key = config.get(BackupSettings.encryption_key)
        # repos
        self._smb_settings = config.get(BackupSettings.backup_to_smb) or {}
        self._aws_s3_settings = config.get(BackupSettings.backup_to_aws_s3) or {}
        self._azure_storage_settings = config.get(BackupSettings.backup_to_azure) or {}
        self._build_version = loads(METADATA_PATH.read_text()).get('Version')

    def _get_db_names(self) -> list:
        dbs = self.db_client.list_database_names()
        dbs_to_filter = ['aggregator', 'local']
        return list(filter(lambda db_name: db_name not in dbs_to_filter, dbs))

    def _set_master_hostname(self) -> str:
        node_metadata = self.db_client.get_database(CORE_UNIQUE_NAME).get_collection('nodes_metadata').find_one(
            {NODE_ID: self.pluginbase_instance.node_id})
        self._host_name = node_metadata['hostname'] if node_metadata.get('hostname') else 'Master'

    def _backup_file_size(self) -> float:
        return round((AXONIUS_BACKUP_PATH / self.filename).stat().st_size / BYTES_TO_MB, 2)

    @staticmethod
    def clean_backup_folder():
        if AXONIUS_BACKUP_PATH.exists():
            shutil.rmtree(AXONIUS_BACKUP_PATH)

    def _get_aggregator_collections_to_exclude(self) -> list:
        """
        return aggregator table collection exclusion list base on backup configuration
        - includeHistory
        - includeUsersAndDevices
        :return: list of collection names.
        """
        return list(
            filter(lambda col:
                   not aggregator_collection_filter(col, self.include_history, self.include_devices_users_data),
                   self.db_client.aggregator.list_collection_names())
        )

    @property
    def version(self) -> str:
        return 'DEVELOP' if self._build_version in ['none', ''] else self._build_version.replace('.', '_')

    @property
    def filename(self) -> str:
        """
        backup file name to be exported to repository.
        :return:
        """
        # format logic base on version and number backups ,hostname ?
        if self.override_previous_backups:
            return f'axonius_{self.version}_{self._host_name}_backup.gpg.tar'

        timestamp = datetime.utcnow().strftime('%Y%m%d')
        return f'axonius_{self.version}_{self._host_name}_{timestamp}_backup.gpg.tar'

    def get_mongo_documents_size(self) -> float:
        """"
            calculate collections docs size per table base on backup configuration.
            :return space alocated in GB
        """

        dbs = self._get_db_names()

        size_of_databases_without_aggregator = sum([
            get_database_data_size(self.db_client.get_database(db_name)) for db_name in dbs
        ])

        aggregator_collections_to_backup = list(
            filter(lambda col: aggregator_collection_filter(col, self.include_history, self.include_devices_users_data),
                   self.db_client.aggregator.list_collection_names())
        )

        aggregator_size = sum(get_collection_storage_size(self.db_client.aggregator.get_collection(col_name))
                              for col_name in aggregator_collections_to_backup)

        return (aggregator_size / (1024 ** 3)) + size_of_databases_without_aggregator

    def check_local_free_disk_space(self) -> bool:
        """
            compare the size of tables to backup with host free disk space .
            making sure it want reduce free space above half current available.
            plus a safety guard 3 times for tar packaging
        :return: True if estimated disk consumption is above criteria.
        """
        host_free_space_in_gb = get_free_disk_space() / BYTES_TO_GB
        backup_data_uncompress_in_gb = get_mongo_space_documents_size(self.include_history,
                                                                      self.include_devices_users_data)

        if backup_data_uncompress_in_gb * AVG_COMPRESSION_RATIO < host_free_space_in_gb / 3:
            return True

        self._log_activity_backup_skip_no_free_space_left(self.include_history,
                                                          host_free_space_in_gb)
        return False

    def check_external_repo_free_space(self):
        pass

    def mongodump(self, db_name, collections_to_exclude=None, compress_and_sign=False):
        """
        mongodump version 100.2
        - dump all tables or collection per table
        - collection exclusion can be done on single table
        - mongodump is a none blocking process.

        :param db_name: db table name
        :param collections_to_exclude:  list of collection of a given table to exlude
        :param compress_and_sign:  add gzip and output stream into gpg process to sign usign pre shared key
        :return:
        """

        try:
            cmd = (f'mongodump --quiet --uri="mongodb://{self.db_user}:{self.db_pass}@{self.db_host}'
                   f'/{db_name}?authSource=admin"')

            if collections_to_exclude:
                cmd += ' '.join(f' --excludeCollection={col}' for col in collections_to_exclude)

            if compress_and_sign:
                #   --archive => mongodump support of output stream in order to pipe to another process.
                #  create subprocess with stdout as pipeline into 2nd subprocess to communicate as recommanded in docs

                cmd += ' --gzip  --archive'
                gpg_cmd = (f'gpg --passphrase {self.pre_shared_key} --symmetric --cipher-algo {self.cipher_algo} '
                           f'--output {AXONIUS_BACKUP_PATH}/{db_name}.gz.gpg')
                logger.debug(f'mongodump cmd={cmd}')

                if self.pre_shared_key is None or len(self.pre_shared_key) < 16:
                    raise BackupException('invalid pre-shared-key - aborting backup ! ')

                try:
                    mongodump = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    subprocess.check_output(shlex.split(gpg_cmd), stdin=mongodump.stdout, timeout=BACKUP_TIMEOUT_12H)
                    cmd_out, cmd_err = mongodump.communicate(timeout=BACKUP_TIMEOUT_12H)
                except subprocess.TimeoutExpired:
                    mongodump.kill()
                    cmd_out, cmd_err = mongodump.communicate()
                    raise BackupException(f'Mongodump command pipeline with encryption timeout!'
                                          f' stderr={cmd_err} output={cmd_out}')

                if mongodump.returncode != 0:
                    raise BackupException(f'Mongodump Error - Return code is {mongodump.returncode}\n'
                                          f'stderr={cmd_err}\n output={cmd_out}')

            else:
                cmd += f' --out={AXONIUS_BACKUP_PATH}/dump'
                subprocess.check_output(shlex.split(cmd), timeout=BACKUP_TIMEOUT_12H)

        except subprocess.CalledProcessError as pe:
            logger.exception('mongodump subprocess pipeline failure')
            raise BackupException(f'Mongodump failure with CMD={pe.cmd} ERROR={pe.stderr} Output={pe.output}')

        except subprocess.TimeoutExpired:
            logger.exception('mongodump  command timeout ')
            raise BackupException(f'mongodump command timeout cmd={cmd}')

        except ValueError:
            raise BackupException(f'mongodump invalid command: cmd={cmd}')

    def _check_max_days_since_last_backup(self) -> bool:
        """
        check triggerable_history for backup jobs results.
        look for latest successful upload.
        :return: True if match max days since last backup or days value set to zero.
        """

        if self.min_days_between_cycles == 0:
            return True

        last_successful_backup = self.db_client.get_database(SYSTEM_SCHEDULER_PLUGIN_NAME)\
            .get_collection(TRIGGERABLE_HISTORY).find_one({
                'job_name': 'backup',
                'job_completed_state': SUCCESSFUL,
                f'result.{BACKUP_UPLOADS_STATUS}': SUCCESSFUL
            }, {JOB_FINISHED_AT: 1}, sort=[(JOB_FINISHED_AT, pymongo.DESCENDING)])

        last_successful_backup = last_successful_backup.get(JOB_FINISHED_AT) if last_successful_backup else None

        if (last_successful_backup is None
                or (datetime.utcnow() - last_successful_backup) > timedelta(days=self.min_days_between_cycles)):
            logger.info(f'match max days since last backup done on {last_successful_backup}  ')
            return True

        self.pluginbase_instance.log_activity(AuditCategory.Backup, AuditAction.Skip, {
            'cause': f'Min days between backup set to {str(self.min_days_between_cycles)} '
                     f'days and last backup was {str((datetime.utcnow() - last_successful_backup)).split(".")[0]} ago.'
        })
        return False

    def _tar_packing(self):
        """
        final packaging will include

        - aggregator.gz.gpg
        - db_backup.zip.gpg
        - build metadata (for version )

        """
        # Final TAR packing
        with tarfile.open(f'{AXONIUS_BACKUP_PATH}/{self.filename}', 'w') as tar:
            tar.add(METADATA_PATH, arcname=METADATA_PATH.name)
            backup_filename = self.filename
            for file_path in AXONIUS_BACKUP_PATH.iterdir():
                if file_path.name != backup_filename:
                    tar.add(file_path, arcname=file_path.name, recursive=False)
                    os.unlink(file_path)

    def start(self):
        try:
            # check backup criteria
            if self._check_max_days_since_last_backup() is False:
                return SKIPPED

            if self.check_local_free_disk_space() is False:
                return SKIPPED_OUT_OF_SPACE

            self._log_activity_backup_start()
            start_time = datetime.utcnow()

            # PHASE 1 - aggregator history device and users data
            self._create_backup_folder()  # required by gpg
            self.mongodump('aggregator', self._get_aggregator_collections_to_exclude(), compress_and_sign=True)

            # PHASE 2 - all other db tables
            for db_name in self._get_db_names():
                self.mongodump(db_name)

            zip_stream = BytesIO()
            with zipfile.ZipFile(zip_stream, 'w') as zf:
                for file_path in AXONIUS_BACKUP_PATH.rglob('dump/**/*'):
                    if file_path.is_file():
                        zf.write(file_path, arcname='dump/' + str(file_path).split('dump/')[1],
                                 compress_type=zipfile.ZIP_DEFLATED)
                        os.unlink(file_path)
                shutil.rmtree(f'{AXONIUS_BACKUP_PATH}/dump')

                for file_path in AXONIUS_SETTINGS_PATH.iterdir():
                    if file_path.is_file():
                        zf.write(file_path, arcname=f'.axonius_settings/{file_path.name}',
                                 compress_type=zipfile.ZIP_DEFLATED)
            self.gpg_zip_stream(zip_stream)
            zip_stream.close()
            logger.info('done generating db_backup zipfile')

            self._tar_packing()
            backup_generation_time = datetime.utcnow() - start_time
            logger.info(f'backup file generation done -  took {backup_generation_time} size {self._backup_file_size()}')
            self._log_activity_backup_file_ready(backup_generation_time, self._backup_file_size())

            # UPLOADS TO EXTERNAL REPOSITORIES:
            repos = self.get_external_repos_to_upload()
            backup_uploads_result = True
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(repos)) as executor:
                upload_to = {executor.submit(func, settings): type for type, func, settings in repos}

                for future in concurrent.futures.as_completed(upload_to):
                    try:
                        repo_type = upload_to[future]
                        future.result()
                        self._log_activity_upload_file_completed(repo_type.value)
                    except Exception:
                        logger.exception(f'Upload failure to {repo_type.value} backup file was not successful')
                        backup_uploads_result = False

            return ({BACKUP_UPLOADS_STATUS: SUCCESSFUL, BACKUP_FILE_NAME: self.filename} if backup_uploads_result
                    else {BACKUP_UPLOADS_STATUS: FAILURE,  BACKUP_FILE_NAME: self.filename or ''})

        except Exception:
            logger.exception('Backup file generation failure !')
            # clean up dump leftovers
            self.clean_backup_folder()
            self._log_activity_backup_failure(cause='failed to create backup file')

        finally:
            self.clean_backup_folder()

    def _create_backup_folder(self):
        try:
            os.makedirs(AXONIUS_BACKUP_PATH)
        except OSError:
            # backup leftovers clean them all
            self.clean_backup_folder()
            os.makedirs(AXONIUS_BACKUP_PATH)
        except Exception as e:
            raise BackupException(e)

    def gpg_zip_stream(self, zip_stream):
        """
        encrypt zip stream with GPG, input stream pipline to gpg sub process
        stream will be closed when done.
        :param zip_stream: - in memory zip stream instance
        """
        gpg_cmd = (f'gpg --passphrase {self.pre_shared_key} --symmetric --cipher-algo {self.cipher_algo} '
                   f'--output {AXONIUS_BACKUP_PATH}/db_backup.zip.gpg')
        try:

            gpg_proc = subprocess.Popen(shlex.split(gpg_cmd), stdin=subprocess.PIPE)
            cmd_out, cmd_err = gpg_proc.communicate(zip_stream.getvalue(), timeout=BACKUP_TIMEOUT_12H)
            if gpg_proc.returncode != 0:
                raise BackupException(f'gpg zip stream fatal error stderr={cmd_err} output={cmd_out}')

        except subprocess.CalledProcessError as pe:
            raise BackupException(f'GPG db backup zip fatal error CMD={pe.cmd} ERROR={pe.stderr} Output={pe.output}')

        except Exception as e:
            raise BackupException(f'fatal error during backup encryption  Reason: {repr(e)}')

        finally:
            zip_stream.close()

    def _log_activity_backup_start(self):
        """
        log audit for backup start
        """
        try:
            self.pluginbase_instance.log_activity(AuditCategory.Backup, AuditAction.Start, {
                'include_devices_users_data': ('include devices/user data and '
                                               if self.include_devices_users_data else ''),
                'include_history': 'include history' if self.include_history else 'without history',
            })

        except Exception:
            logger.exception(f'Error logging audit for backup start')

    def _log_activity_backup_skip_no_free_space_left(self, include_history: str, free_space: float):
        """
        log audit out of space
        """
        try:
            with_history = 'with archive history enabled ' if include_history is True else ''

            cause = f'not enough free space available for backup {with_history} , current available space is ' \
                    f'{str(free_space)}'

            self.pluginbase_instance.log_activity(AuditCategory.Backup, AuditAction.Skip, {
                'cause': cause
            })

            self.pluginbase_instance.create_notification(title='Backup skip not enough available free space left',
                                                         content=cause,
                                                         severity_type='error')

        except Exception:
            logger.exception(f'Error logging audit for backup out of space')

    def _log_activity_backup_failure(self, cause: str):
        """
        log audit backup failure
        """
        try:
            self.pluginbase_instance.log_activity(AuditCategory.Backup, AuditAction.Failure, {
                'cause': cause
            }, AuditType.Error)

            self.pluginbase_instance.create_notification(title='Backup failure',
                                                         content=cause,
                                                         severity_type='error')

        except Exception:
            logger.exception(f'Error logging audit for backup failure ')

    def _log_activity_backup_file_ready(self, duration: str, file_size: float):
        """
        log audit backup file is ready
        """
        try:
            self.pluginbase_instance.log_activity_default(AuditCategory.Backup.value, 'backup_file_ready', {
                'duration': str(duration).split('.')[0],
                'file_size_mb': str(file_size)
            }, AuditType.Info)

        except Exception:
            logger.exception(f'Error logging audit for backup file ready to copy  ')

    def _log_activity_upload_file_event(self, event: str, repo_name: str):
        self.pluginbase_instance.log_activity_default(AuditCategory.Backup.value, f'upload.{event}', {
            'file_name': self.filename,
            'repo': repo_name
        }, AuditType.Info)

    def _log_activity_upload_file_start(self, repo_name: str):
        self._log_activity_upload_file_event('start', repo_name)

    def _log_activity_upload_file_completed(self, repo_name: str):
        self._log_activity_upload_file_event('completed', repo_name)

    def upload_to_smb(self, settings: dict):
        try:
            smb_client = SMBClient(ip=settings.get(BackupRepoSmb.ip),
                                   port=settings.get(BackupRepoSmb.port),
                                   share_name=settings.get(BackupRepoSmb.path),
                                   username=settings.get(BackupRepoSmb.user) or '',
                                   password=settings.get(BackupRepoSmb.password) or '',
                                   use_nbns=bool(settings.get(BackupRepoSmb.use_nbns)),
                                   smb_host=settings.get(BackupRepoSmb.hostname))

        except Exception as err:
            logger.exception(f'Unable to create the SMB client: {err}')
            self._log_activity_backup_failure(cause='SMB connections failure')
            raise

        try:
            self._log_activity_upload_file_start(ExternalRepoType.SMB.value)

            try:
                smb_client.check_read_write_permissions_unsafe()
            except ConnectionError:
                self._log_activity_backup_failure(cause='SMB share missing write permissions')
                raise

            smb_client.upload_files_to_smb([self.filename], source_files_path=str(AXONIUS_BACKUP_PATH))
            logger.info(f'Upload backup to SMB share finished')

        except Exception:
            logger.exception('upload file to smb share failure')
            ip = settings.get('ip', '')
            share = settings.get('smb_path', '')
            self._log_activity_backup_failure(cause=f'SMB file upload failed to {ip}@:{share}')
            raise

    def upload_to_s3(self, settings: dict):
        aws_bucket_name = settings.get(BackupRepoAws.bucket_name)
        aws_access_key_id = settings.get(BackupRepoAws.access_key_id)
        aws_secret_access_key = settings.get(BackupRepoAws.secret_access_key)
        key_name = self.filename

        # check bucket s3:PutObject and s3:DeleteObject permissions by temp file u/l
        with NamedTemporaryFile() as temp_file:
            temp_file_name = 'axonius_test'
            try:
                upload_file_to_s3(aws_bucket_name,
                                  temp_file_name,
                                  temp_file,
                                  aws_access_key_id,
                                  aws_secret_access_key)
                try:
                    delete_file_from_s3(aws_bucket_name,
                                        temp_file_name,
                                        aws_access_key_id,
                                        aws_secret_access_key)

                except Exception as e:
                    logger.exception(f'Failed deleting .axonius_test file. {str(e)}')
                    raise
            except Exception as e:
                msg = f'AWS S3 missing sufficient bucket permission bucket {aws_bucket_name} ' \
                      f'write/delete permissions'
                self._log_activity_backup_failure(cause=msg)
                logger.exception(f'{msg} {str(e)}')
                raise ConnectionError(msg)

        self._log_activity_upload_file_start(ExternalRepoType.AWS.value)

        try:
            with open(f'{AXONIUS_BACKUP_PATH}/{self.filename}', 'rb') as file_obj:
                upload_file_to_s3(aws_bucket_name, key_name, file_obj, aws_access_key_id, aws_secret_access_key)
                logger.info(f'Completed S3 backup file name: {key_name}')

            logger.info(f'Completed S3 upload file name: {key_name}')

        except Exception as e:
            logger.exception(f'Backup upload failure to s3: {str(e)}')
            self._log_activity_backup_failure(cause=f'AWS S3 file upload failed to bucket {aws_bucket_name}')
            raise

    def upload_to_azure(self, settings: dict):
        try:
            container_name = settings.get(BackupRepoAzure.container_name)
            connection_string = settings.get(BackupRepoAzure.connection_string)
            azure_storage_client = AzureBlobStorageClient(
                connection_string=connection_string,
                container_name=container_name)

            # verify container exists
            is_container_exsits = False
            azure_storage_client.get_blob_containers()
            for container in azure_storage_client.blob_containers:
                if isinstance(container, AzureBlobContainer) and container_name == container.name:
                    is_container_exsits = True
                    break
            if is_container_exsits is False:
                raise BackupException(f'Azure storage container name {container_name} does not exists')

            # check we can write permission for blob
            with NamedTemporaryFile(dir='/tmp') as temp_file:
                temp_file_name = 'axonius_backup_test'
                if not azure_storage_client.block_upload_blob(container_name=container_name,
                                                              blob_name=temp_file_name,
                                                              blob_path=temp_file.name):
                    msg = f'missing sufficient blob permission container named {container_name} write permissions'
                    self._log_activity_backup_failure(cause=msg)
                    raise ConnectionError(msg)

                if not azure_storage_client.delete_blob(container_name=container_name, blob_name=temp_file_name):
                    msg = f'missing sufficient blob permission container named {container_name} delete permissions'
                    self._log_activity_backup_failure(cause=msg)
                    raise ConnectionError(msg)

            self._log_activity_upload_file_start(ExternalRepoType.AZURE.value)

            # azure blob doesnt support overwrite so need to be deleted if already created
            azure_storage_client.get_blobs(container_name)
            for blob in azure_storage_client.blobs[container_name]:
                if isinstance(blob, AzureBlob) and self.filename == blob.name and self.override_previous_backups:
                    status = azure_storage_client.delete_blob(
                        container_name=container_name,
                        blob_name=self.filename)
                    if not status:
                        raise BackupException(f'Unable to delete existing blob {self.filename} '
                                              f'from Azure storage container name {container_name}')
                    break

            upload_status = azure_storage_client.block_upload_blob(
                container_name=container_name,
                blob_name=self.filename,
                blob_path=f'{AXONIUS_BACKUP_PATH}/{self.filename}'
            )

            if upload_status:
                logger.info(f'Completed file upload to azure storage container name {container_name} '
                            f'file name{self.filename}')
            else:
                raise BackupException(f'azure storage upload file {self.filename} failed to container {container_name}')

        except Exception as e:
            logger.exception(f'Backup upload failure to azure storage: {str(e)}')
            self._log_activity_backup_failure(cause=f'Azure Storage file upload failed to container {container_name}')
            raise

    def get_external_repos_to_upload(self) -> list:
        """
        check configuration for enabled backup repos
        return tuple of ( REPO_TYPE, UPLOAD_FUNC, REPO_SETTINGS )
        :return: list[tuple]
        """
        repos = []
        if self._smb_settings.get(BackupRepoSmb.enabled):
            repos.append((ExternalRepoType.SMB, self.upload_to_smb, self._smb_settings))
        if self._aws_s3_settings.get(BackupRepoAws.enabled):
            repos.append((ExternalRepoType.AWS, self.upload_to_s3, self._aws_s3_settings))
        if self._azure_storage_settings.get(BackupRepoAzure.enabled):
            repos.append((ExternalRepoType.AZURE, self.upload_to_azure, self._azure_storage_settings))
        return repos
