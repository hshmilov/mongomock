# pylint: disable=too-many-branches, too-many-statements, protected-access
import datetime
import io
import json
import logging
import os
import subprocess
import tarfile

from funcy import chunks

from axonius.clients.aws.utils import upload_file_to_s3
from axonius.entities import EntityType
from axonius.plugin_base import PluginBase
from axonius.utils.host_utils import get_free_disk_space
from axonius.utils.json_encoders import IteratorJSONEncoder
from axonius.utils.smb import SMBClient

logger = logging.getLogger(f'axonius.{__name__}')

DISK_SPACE_FREE_GB_MANDATORY = 15
AXONIUS_BACKUP_FILENAME = 'axonius_backup.tar.gz'
BYTES_TO_GIGABYTES = 1024 ** 3
RETURN_SUCCESS_CODE = 0
RETURN_FAILURE_CODE = 1


# pylint: disable=invalid-triple-quote
def verify_preshared_key(preshared_key: str):
    """
    Ensure that the PSK is at least 16 chars or surface an error.

    :param str preshared_key: A string of 16 or more characters, input in
    Settings | General Settings of the GUI
    """
    if isinstance(preshared_key, str):
        if len(str(preshared_key or '')) < 16:
            raise ValueError(f'Key must be at least 16 characters, got '
                             f'{len(preshared_key)}')


def check_disk_space():
    """
    Check if there is enough space on this machine. Otherwise surface the error.
    """
    free_disk_space_in_gb = get_free_disk_space() / (BYTES_TO_GIGABYTES)

    if free_disk_space_in_gb < DISK_SPACE_FREE_GB_MANDATORY:
        message = f'Error - only {free_disk_space_in_gb}gb is left on disk, ' \
                  f'while {DISK_SPACE_FREE_GB_MANDATORY} is required'
        raise ValueError(message)


def unlink_existing_files():
    """ Delete any existing backup files on the Axonius host. """
    try:
        if os.path.exists(AXONIUS_BACKUP_FILENAME):
            os.unlink(AXONIUS_BACKUP_FILENAME)
        logger.info(f'Unlinking {AXONIUS_BACKUP_FILENAME}')
    except Exception:
        logger.exception(f'Unable to unlink file: {AXONIUS_BACKUP_FILENAME}')
    try:
        if os.path.exists(f'{AXONIUS_BACKUP_FILENAME}.gpg'):
            os.unlink(f'{AXONIUS_BACKUP_FILENAME}.gpg')
        logger.info(f'Unlinking {AXONIUS_BACKUP_FILENAME}.gpg')
    except Exception:
        logger.exception(f'Unable to unlink file: {AXONIUS_BACKUP_FILENAME}.gpg')


def add_cursor_to_tar(tar_obj: tarfile, cursor_obj: PluginBase.Instance, entity_name: str):
    """
    Build the tar file in bite-sized pieces. Delicious.

    :param tar_obj: A tarfile type file object
    :param cursor_obj: A PluginBAse.Instance object
    :param entity_name: A name for the entity in the cursor
    """
    total = 0
    estimated_count = cursor_obj.count()
    for i, entities in enumerate(chunks(5000, cursor_obj)):
        total += len(entities)
        tarinfo = tarfile.TarInfo(f'{entity_name}_{i}')
        try:
            data = json.dumps(entities, cls=IteratorJSONEncoder).encode('utf-8')
        except Exception:
            logger.exception(f'Unable to dump JSON data: {tarinfo}')
            raise
        tarinfo.size = len(data)
        try:
            tar_obj.addfile(tarinfo, io.BytesIO(data))
        except Exception:
            logger.exception(f'Unable to add data to tarfile: {data}')
            raise
        logger.info(f'Backup to external: Finished adding {total} / '
                    f'{estimated_count} of type {entity_name} to tarfile')
    logger.info(f'Finished adding cursors to tar file')


#pylint: disable=protected-access
def create_tar_file():
    """ Create a compressed tar archive of the update file. """
    with tarfile.open(AXONIUS_BACKUP_FILENAME, 'w:gz') as tar:
        add_cursor_to_tar(tar_obj=tar,
                          cursor_obj=PluginBase.Instance.devices_db.find({}),
                          entity_name='devices')
        add_cursor_to_tar(tar_obj=tar,
                          cursor_obj=PluginBase.Instance.users_db.find({}),
                          entity_name='users')
        add_cursor_to_tar(tar_obj=tar,
                          cursor_obj=PluginBase.Instance._raw_adapter_entity_db_map[EntityType.Devices].find({}),
                          entity_name='raw_devices')
        add_cursor_to_tar(tar_obj=tar,
                          cursor_obj=PluginBase.Instance._raw_adapter_entity_db_map[EntityType.Users].find({}),
                          entity_name='raw_users')
        add_cursor_to_tar(tar_obj=tar,
                          cursor_obj=PluginBase.Instance._all_fields_db_map[EntityType.Devices].find({}),
                          entity_name='fields_devices')
        add_cursor_to_tar(tar_obj=tar,
                          cursor_obj=PluginBase.Instance._all_fields_db_map[EntityType.Users].find({}),
                          entity_name='fields_users')
        add_cursor_to_tar(tar_obj=tar,
                          cursor_obj=PluginBase.Instance.adapter_client_labels_db.find({}),
                          entity_name='adapter_client_labels')


def encrypt_tar_file(preshared_key: str) -> int:
    """
    Encrypt the tar file and return a response to the caller. The
    response is rarely used, but is important in troubleshooting.

    :param str preshared_key: A string of >16 characters, input in the
    Settings | General Settings of the GUI
    :return response: A numeric status code showing the results of the
    encryption process.
    """
    response = subprocess.check_call([
        'gpg', '--output', f'{AXONIUS_BACKUP_FILENAME}.gpg',
        '--passphrase', preshared_key,
        '--symmetric', AXONIUS_BACKUP_FILENAME
    ])
    logger.info(f'Tarfile encryption status code: {response}')
    return response


def backup_to_external(services: list) -> int:
    """
    This is the jump off point for all supported export types (S3, SMB, etc.).
    This code is transitioning from a stand-alone S3 backup to a multi-service
    backup and should be used going forward.

    :param list services: The list of the services to backup to (s3, smb)
    :returns int return_code:
    """
    return_code = RETURN_FAILURE_CODE

    # Check if there is enough space on this machine.
    check_disk_space()

    # remove any existing files
    unlink_existing_files()

    # launch the backup
    try:
        if 's3' in services:
            try:
                return_code = backup_to_s3()
                logger.info(f'Backup to S3 finished.')
            except Exception:
                logger.exception(f'Backup to S3 failed.')
                return_code = RETURN_FAILURE_CODE
        if 'smb' in services:
            try:
                return_code = backup_to_smb()
                logger.info(f'Backup to SMB finished.')
            except Exception:
                logger.exception(f'Backup to SMB failed.')
                return_code = RETURN_FAILURE_CODE

    except Exception as err:
        logger.exception(f'General backup failure: {err}')
        return_code = RETURN_FAILURE_CODE

    return return_code


# pylint: disable=protected-access, too-many-branches, too-many-statements
def backup_to_smb() -> int:
    """
    Collect the relevant settings from the GUI, encrypt the tar file
    and upload the file to the SMB share.

    :returns int return_code: A numeric value showing success (0) or
    failure (1). If there are configuration errors, those errors are raised
    and no return code will be sent to the caller. This is needed to support
    the API and prevents an HTTP 500 error.
    """
    logger.info('Backup to SMB: Starting.')

    # create the tar file with cursors
    create_tar_file()

    try:
        smb_settings = PluginBase.Instance._smb_settings.copy()
    except Exception:
        logger.exception(f'Unable to get the SMB settings from PluginBase')
        raise

    if not smb_settings.get('enabled'):
        raise ValueError(f'SMB integration is not enabled.')

    if not smb_settings.get('enable_backups'):
        raise ValueError(f'SMB Backups are not enabled.')

    if not smb_settings.get('hostname'):
        raise ValueError(f'SMB hostname address is not set.')
    hostname = smb_settings.get('hostname')

    if not smb_settings.get('ip'):
        raise ValueError(f'SMB IP address is not set.')
    ip = smb_settings.get('ip')

    share_name = smb_settings.get('share_path')
    if not share_name:
        raise ValueError(f'SMB share path not found.')
    share_name = share_name.replace('\\', '/')

    nbns = smb_settings.get('use_nbns')
    if isinstance(nbns, bool):
        use_nbns = nbns
    else:
        use_nbns = False

    # Check the PSK to make sure it conforms to known standard/strength
    preshared_key = smb_settings.get('preshared_key')
    if not preshared_key:
        raise ValueError(f'Backup Pre-Shared Key is not set.')

    verify_preshared_key(preshared_key)

    # encrypt the tar file
    try:
        status = encrypt_tar_file(preshared_key)
    except Exception:
        logger.exception(f'GPG encryption failed. Stopping.')
        return RETURN_FAILURE_CODE

    if status == RETURN_SUCCESS_CODE:
        try:
            os.unlink(AXONIUS_BACKUP_FILENAME)
            logger.info(f'Unlinked {AXONIUS_BACKUP_FILENAME}')
        except Exception:
            logger.exception(f'Unable to unlink {AXONIUS_BACKUP_FILENAME}')

    try:
        smb_client = SMBClient(ip=ip,
                               smb_host=hostname,
                               username=smb_settings.get('username') or '',
                               password=smb_settings.get('password') or '',
                               share_name=share_name,
                               port=smb_settings.get('port'),
                               use_nbns=use_nbns)
    except Exception as err:
        logger.exception(f'Unable to create the SMB client: {err}')
        return RETURN_FAILURE_CODE

    try:
        smb_client.upload_files_to_smb([f'{AXONIUS_BACKUP_FILENAME}.gpg'])
        logger.info(f'Backup to SMB share {share_name} finished')
        return_code = RETURN_SUCCESS_CODE
    except Exception:
        logger.exception(f'Could not upload {AXONIUS_BACKUP_FILENAME}.gpg '
                         f'to {hostname}/{share_name} @ {ip}')
        return_code = RETURN_FAILURE_CODE
    finally:
        try:
            if os.path.exists(AXONIUS_BACKUP_FILENAME):
                os.unlink(AXONIUS_BACKUP_FILENAME)
                logger.info(f'Unlinking {AXONIUS_BACKUP_FILENAME}')
        except Exception:
            logger.exception(f'Unable to unlink {AXONIUS_BACKUP_FILENAME}')
        try:
            if os.path.exists(f'{AXONIUS_BACKUP_FILENAME}.gpg'):
                os.unlink(f'{AXONIUS_BACKUP_FILENAME}.gpg')
                logger.info(f'Unlinking {AXONIUS_BACKUP_FILENAME}.gpg')
        except Exception:
            logger.exception(f'Unable to unlink {AXONIUS_BACKUP_FILENAME}.gpg')

    return return_code


# pylint: disable=too-many-branches, too-many-statements
def backup_to_s3() -> int:
    """
    Creates an encrypted archive of devices, users & fields and uploads to s3.
    :return:
    """
    return_code = RETURN_FAILURE_CODE

    try:
        logger.info('Backup to s3: Starting.')
        aws_s3_settings = PluginBase.Instance._aws_s3_settings.copy()
        # Check configs
        if not aws_s3_settings.get('enabled') or not aws_s3_settings.get('enable_backups'):
            raise ValueError(f'S3 Settings / Backup is not enabled')

        aws_access_key_id = aws_s3_settings.get('aws_access_key_id')
        aws_secret_access_key = aws_s3_settings.get('aws_secret_access_key')
        aws_bucket_name = aws_s3_settings.get('bucket_name')
        preshared_key = aws_s3_settings.get('preshared_key')

        if (aws_access_key_id and not aws_secret_access_key) or (aws_secret_access_key and not aws_access_key_id):
            raise ValueError(f'AWS access key id / secret access key - Both or None should exist')

        if not aws_bucket_name:
            raise ValueError(f'Bucket name does not exist')

        verify_preshared_key(preshared_key)

        # Check if there is enough space on this machine. Otherwise stop the process
        free_disk_space_in_gb = get_free_disk_space() / (1024 ** 3)
        if free_disk_space_in_gb < DISK_SPACE_FREE_GB_MANDATORY:
            message = f'Error - only {free_disk_space_in_gb}gb is left on disk, ' \
                f'while {DISK_SPACE_FREE_GB_MANDATORY} is required'
            raise ValueError(message)

        if os.path.exists(AXONIUS_BACKUP_FILENAME):
            os.unlink(AXONIUS_BACKUP_FILENAME)
        if os.path.exists(f'{AXONIUS_BACKUP_FILENAME}.gpg'):
            os.unlink(f'{AXONIUS_BACKUP_FILENAME}.gpg')

        # Create an archive of the update file.
        with tarfile.open(AXONIUS_BACKUP_FILENAME, 'w:gz') as tar:
            add_cursor_to_tar(tar, PluginBase.Instance.devices_db.find({}), 'devices')
            add_cursor_to_tar(tar, PluginBase.Instance.users_db.find({}), 'users')
            add_cursor_to_tar(
                tar, PluginBase.Instance._raw_adapter_entity_db_map[EntityType.Devices].find({}), 'raw_devices')
            add_cursor_to_tar(
                tar, PluginBase.Instance._raw_adapter_entity_db_map[EntityType.Users].find({}), 'raw_users')
            add_cursor_to_tar(
                tar, PluginBase.Instance._all_fields_db_map[EntityType.Devices].find({}), 'fields_devices')
            add_cursor_to_tar(
                tar, PluginBase.Instance._all_fields_db_map[EntityType.Users].find({}), 'fields_users')
            add_cursor_to_tar(
                tar, PluginBase.Instance.adapter_client_labels_db.find({}), 'adapter_client_labels')

        # Encrypt
        subprocess.check_call([
            'gpg', '--output', f'{AXONIUS_BACKUP_FILENAME}.gpg',
            '--passphrase', preshared_key,
            '--symmetric', AXONIUS_BACKUP_FILENAME
        ])

        # Delete unencrypted file
        os.unlink(AXONIUS_BACKUP_FILENAME)

        file_size_in_mb = round(os.stat(f'{AXONIUS_BACKUP_FILENAME}.gpg').st_size / (1024 ** 2), 2)
        logger.info(f'Backup to s3: Encrypted file size: {file_size_in_mb}mb')

        try:
            system_id_response = PluginBase.Instance.request_remote_plugin('system_id')
            if system_id_response.status_code != 200:
                raise ValueError(f'Error in response. '
                                 f'Status code: {system_id_response.status_code}: {system_id_response.text}')
            system_id = system_id_response.text
        except Exception:
            logger.exception(f'Could not get system id, setting to unknown')
            system_id = 'unknown'
        key_name = f'axonius_backup_{system_id}_{str(datetime.datetime.now()).replace(" ", "_")}.tar.gz.gpg'
        # Final step: Upload the file to s3
        with open(f'{AXONIUS_BACKUP_FILENAME}.gpg', 'rb') as file_obj:
            upload_file_to_s3(aws_bucket_name, key_name, file_obj, aws_access_key_id, aws_secret_access_key)
            logger.info(f'Completed S3 backup file name: {key_name}')

        return_code = RETURN_SUCCESS_CODE
        logger.info(f'Backup to s3: Finished')
    except Exception as e:
        logger.exception(f'Backup to s3: {str(e)}')
        return_code = RETURN_FAILURE_CODE
    finally:
        try:
            if os.path.exists(AXONIUS_BACKUP_FILENAME):
                os.unlink(AXONIUS_BACKUP_FILENAME)
                logger.info(f'Unlinking {AXONIUS_BACKUP_FILENAME}')
        except Exception:
            logger.exception(f'Unable to unlink {AXONIUS_BACKUP_FILENAME}')
        try:
            if os.path.exists(f'{AXONIUS_BACKUP_FILENAME}.gpg'):
                os.unlink(f'{AXONIUS_BACKUP_FILENAME}.gpg')
                logger.info(f'Unlinking {AXONIUS_BACKUP_FILENAME}.gpg')
        except Exception:
            logger.exception(f'Unable to unlink {AXONIUS_BACKUP_FILENAME}.gpg')

    return return_code
