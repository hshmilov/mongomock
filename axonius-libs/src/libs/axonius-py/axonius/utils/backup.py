import io
import json
import logging
import os
import subprocess
import tarfile
import datetime

from funcy import chunks

from axonius.clients.aws.utils import upload_file_to_s3
from axonius.entities import EntityType
from axonius.plugin_base import PluginBase
from axonius.utils.host_utils import get_free_disk_space
from axonius.utils.json_encoders import IteratorJSONEncoder

logger = logging.getLogger(f'axonius.{__name__}')
DISK_SPACE_FREE_GB_MANDATORY = 15
AXONIUS_BACKUP_FILENAME = 'axonius_backup.tar.gz'


def verify_preshared_key(preshared_key: str):
    if len(str(preshared_key or '')) < 16:
        raise ValueError(f'Key must be at least 16 characters')
    return True


# pylint: disable=too-many-branches, too-many-statements, protected-access
def backup_to_s3():
    """
    Creates an encrypted archive of devices, users & fields and uploads to s3.
    :return:
    """
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

        def add_cursor_to_tar(tar_obj: tarfile, cursor_obj, entity):
            total = 0
            estimated_count = cursor_obj.count()
            for i, entities in enumerate(chunks(5000, cursor_obj)):
                total += len(entities)
                tarinfo = tarfile.TarInfo(f'{entity}_{i}')
                data = json.dumps(entities, cls=IteratorJSONEncoder).encode('utf-8')
                tarinfo.size = len(data)
                tar_obj.addfile(tarinfo, io.BytesIO(data))
                logger.info(f'Backup to s3: Finished adding {total} / {estimated_count} of type {entity}')

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

        logger.info(f'Backup to s3: Finished')
    except Exception as e:
        logger.exception(f'Backup to s3: {str(e)}')
    finally:
        if os.path.exists(AXONIUS_BACKUP_FILENAME):
            os.unlink(AXONIUS_BACKUP_FILENAME)
        if os.path.exists(f'{AXONIUS_BACKUP_FILENAME}.gpg'):
            os.unlink(f'{AXONIUS_BACKUP_FILENAME}.gpg')
