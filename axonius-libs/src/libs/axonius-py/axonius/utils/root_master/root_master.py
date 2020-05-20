"""
Handle all root-master architecture functions.
"""
import json
import logging
import os
import subprocess
import tarfile

from pymongo import ReplaceOne
from pymongo.errors import BulkWriteError
from axonius.utils.smb import SMBClient
from axonius.clients.aws.utils import (
    aws_list_s3_objects,
    download_s3_object_to_file_obj,
    delete_file_from_s3,
    get_s3_key_meta,
)
from axonius.consts.gui_consts import RootMasterNames
from axonius.entities import EntityType
from axonius.plugin_base import PluginBase
from axonius.utils.host_utils import get_free_disk_space
from axonius.utils.backup import verify_preshared_key

logger = logging.getLogger(f'axonius.{__name__}')
DISK_SPACE_FREE_GB_MANDATORY = 15
BYTES_TO_GIGABYTES = 1024 ** 3
BYTES_TO_MEGABYTES = 1024 ** 2
RESTORE_FILE = 'restore.tar.gz'
RESTORE_FILE_GPG = 'restore.tar.gz.gpg'


# pylint: disable=protected-access, too-many-locals, too-many-branches, too-many-statements
def root_master_parse_entities(entity_type: EntityType, info, backup_source=None):
    entities = json.loads(info)
    db = PluginBase.Instance._entity_db_map[entity_type]
    bulk_replacements = []
    for entity in entities:
        entity.pop('_id', None)  # not interesting
        if 'internal_axon_id' not in entity:
            logger.warning(f'Weird device: {entity}')
            continue
        if backup_source:
            try:
                for adapter_entity in entity.get('adapters') or []:
                    if adapter_entity.get('data'):
                        adapter_entity['data']['backup_source'] = backup_source
            except Exception:
                pass
        bulk_replacements.append(ReplaceOne({'internal_axon_id': entity['internal_axon_id']}, entity, upsert=True))

    try:
        db.bulk_write(bulk_replacements, ordered=False)
    except BulkWriteError as bwe:
        logger.exception(f'Error in bulk_write: {bwe.details}')
        raise


def root_master_parse_entities_raw(entity_type: EntityType, info):
    entities = json.loads(info)
    db = PluginBase.Instance._raw_adapter_entity_db_map[entity_type]
    bulk_replacements = []
    for entity in entities:
        entity.pop('_id', None)  # not interesting
        if 'plugin_unique_name' not in entity or 'id' not in entity:
            logger.warning(f'Weird device: {entity}')
            continue
        bulk_replacements.append(
            ReplaceOne({'plugin_unique_name': entity['plugin_unique_name'], 'id': entity['id']}, entity, upsert=True)
        )

    db.bulk_write(bulk_replacements, ordered=False)


def root_master_parse_entities_fields(entity_type: EntityType, info):
    entities = json.loads(info)
    fields_db_map = PluginBase.Instance._all_fields_db_map[entity_type]
    for entity in entities:
        entity.pop('_id', None)  # not interesting
        schema_name = entity.get('name')
        plugin_name = entity.get('plugin_name')
        plugin_unique_name = entity.get('plugin_unique_name')
        if schema_name == 'hyperlink' and plugin_name:
            fields_db_map.replace_one({'name': schema_name, 'plugin_name': plugin_name}, entity, upsert=True)
        elif schema_name in ['parsed', 'dynamic']:
            if plugin_unique_name:
                current_db_items = (
                    (fields_db_map.find_one({'name': schema_name, 'plugin_unique_name': plugin_unique_name}) or {}).get(
                        'schema'
                    )
                    or {}
                ).get('items') or []

                new_schema = (entity.get('schema') or {}).get('items') or []
                new_names = [field['name'] for field in new_schema]

                for current_item in current_db_items:
                    if current_item['name'] not in new_names:
                        new_schema.append(current_item)

                entity['schema']['items'] = new_schema

                fields_db_map.replace_one(
                    {'name': schema_name, 'plugin_unique_name': plugin_unique_name}, entity, upsert=True
                )
        elif schema_name in ['exist', 'raw']:
            field_name = {'exist': 'fields', 'raw': 'raw'}[schema_name]
            exist_fields = entity.get(field_name) or []
            if schema_name == 'exist' and plugin_unique_name == '*':
                # 'backup_source' is a mandatory field in root master
                exist_fields.append('backup_source')
            if exist_fields and plugin_unique_name:
                fields_db_map.update_one(
                    {'name': schema_name, 'plugin_unique_name': plugin_unique_name},
                    {'$addToSet': {field_name: {'$each': exist_fields}}},
                    upsert=True,
                )


def root_master_parse_adapter_client_labels(info):
    try:
        data = json.loads(info)
        db = PluginBase.Instance.adapter_client_labels_db

        for connection in data:
            client_id = connection.get('client_id')
            node_id = connection.get('node_id')
            plugin_unique_name = connection.get('plugin_unique_name')

            if not client_id or not node_id or not plugin_unique_name:
                logger.error(f'Weird connection {connection} not putting')
                continue

            db.replace_one(
                {'client_id': client_id, 'node_id': node_id, 'plugin_unique_name': plugin_unique_name},
                connection,
                upsert=True,
            )
    except Exception:
        logger.exception(f'Failed to parse adapter client labels')


def verify_restore_s3(bucket_name, access_key_id=None, secret_access_key=None):
    """Verify root master enabled s3 settings and available disk space."""
    root_master_settings = PluginBase.Instance.feature_flags_config().get(RootMasterNames.root_key) or {}
    root_master_enabled = root_master_settings.get(RootMasterNames.enabled)

    if not root_master_enabled:
        raise ValueError(f'Central core mode is not enabled')

    if (access_key_id and not secret_access_key) or (secret_access_key and not access_key_id):
        raise ValueError(f'Supply both or neither of access_key_id and secret_access_key')

    if not bucket_name:
        raise ValueError(f'Must supply "bucket_name" or configure Global Settings > Amazon S3 settings')

    disk_free_bytes = get_free_disk_space()
    disk_free_gb = disk_free_bytes / (BYTES_TO_GIGABYTES)
    disk_free_gb_req = DISK_SPACE_FREE_GB_MANDATORY
    if disk_free_gb <= disk_free_gb_req:
        err = f'Available space must be above {disk_free_gb_req} GB, but only {disk_free_gb} GB is available'
        raise ValueError(err)


def root_master_restore_from_s3():
    """
    Gets an update file of devices & users & fields and loads this to the memory
    :return:
    """
    # 1. Check if there is enough memory left to parse this
    # 2. Store the file on the disk. Extract it using the preshared key.
    # 3. load each file to the memory, and parse it (Has to be single threaded) while not in a cycle.
    #    This can also be async.
    try:
        root_master_settings = PluginBase.Instance.feature_flags_config().get(RootMasterNames.root_key) or {}
        delete_backups = root_master_settings.get(RootMasterNames.delete_backups) or False

        aws_s3_settings = PluginBase.Instance._aws_s3_settings.copy()
        access_key_id = aws_s3_settings.get('aws_access_key_id')
        secret_access_key = aws_s3_settings.get('aws_secret_access_key')
        bucket_name = aws_s3_settings.get('bucket_name')
        preshared_key = aws_s3_settings.get('preshared_key')
        aws_s3_enabled = aws_s3_settings.get('enabled')

        if not aws_s3_enabled:
            raise ValueError(f'AWS S3 Settings are not enabled')

        verify_restore_s3(bucket_name=bucket_name, access_key_id=access_key_id, secret_access_key=secret_access_key)

        # Now when we have all settings configured, we can start the process.
        # First, get the list of all keys in the s3 bucket
        list_s3_args = dict(bucket_name=bucket_name, access_key_id=access_key_id, secret_access_key=secret_access_key)
        key_names = [x['Key'] for x in aws_list_s3_objects(**list_s3_args)]
        logger.info(f'S3 keys found: {",".join(key_names)}')

        # For each file, download the file, parse it, set in DB and delete
        for key_name in key_names:
            try:
                restore_from_s3_key(
                    key_name=key_name,
                    bucket_name=bucket_name,
                    access_key_id=access_key_id,
                    secret_access_key=secret_access_key,
                    preshared_key=preshared_key,
                    delete_backups=delete_backups,
                )
            except Exception:
                logger.exception(f'Failure restoring S3 Object {key_name}')

    except Exception:
        logger.exception(f'Root Master Mode: Could not restore from s3')
    finally:
        restore_cleanup()


def restore_cleanup():
    """Cleanup all the files used by restore process."""
    if os.path.exists(RESTORE_FILE_GPG):
        os.unlink(RESTORE_FILE_GPG)
    if os.path.exists(RESTORE_FILE):
        os.unlink(RESTORE_FILE)


def restore_from_s3_key(
        key_name,
        bucket_name,
        preshared_key=None,
        access_key_id=None,
        secret_access_key=None,
        delete_backups=False,
        allow_re_restore=False,
):
    """Download the file, parse it, set in DB and delete."""
    if not preshared_key:
        err = f'Must supply "preshared_key" or configure Global Settings > Amazon S3 settings'
        raise ValueError(err)

    s3_args = dict(bucket_name=bucket_name, access_key_id=access_key_id, secret_access_key=secret_access_key)

    verify_restore_s3(**s3_args)
    restore_cleanup()

    root_master_config = PluginBase.Instance._get_collection('root_master_config', 'core')
    root_master_docs = root_master_config.find({'type': 'parsed_file'})
    key_names_db = [x['key'] for x in root_master_docs]
    key_already_parsed = key_name in key_names_db

    re_restored = False
    if key_already_parsed:
        if allow_re_restore is not True:
            err = (
                f'S3 object {key_name!r} in bucket {bucket_name!r} already processed and "allow_re_restore" is not True'
            )
            raise ValueError(err)
        re_restored = True

    try:
        try:
            obj_meta = get_s3_key_meta(key_name=key_name, **s3_args)
        except Exception as exc:
            raise ValueError(f'Unable to find S3 Object {key_name!r} in bucket {bucket_name!r}, error: {exc}')

        if not obj_meta:
            valid = '\n  ' + ('\n  '.join([x['Key'] for x in aws_list_s3_objects(**s3_args)]) or 'NONE!')
            raise ValueError(f'Unable to find S3 Object {key_name!r} in bucket {bucket_name!r}, found:{valid}')

        disk_free_bytes = get_free_disk_space()
        disk_free_gb = disk_free_bytes / (BYTES_TO_GIGABYTES)
        obj_bytes = obj_meta['ContentLength']
        obj_gb = obj_bytes / (BYTES_TO_GIGABYTES)
        check_gb = obj_bytes * 2

        if check_gb >= disk_free_bytes:
            # we require two times the size because we also need to gpg-decrypt this file.
            msg = (
                f'Unable to restore S3 object {key_name!r} from bucket {bucket_name!r} with size of {obj_gb} GB - '
                f'Available space must be above {check_gb} GB but only {disk_free_gb} GB is available'
            )
            raise ValueError(msg)

        try:
            logger.info(f'Downloading backup file: {key_name}')
            with open(RESTORE_FILE_GPG, 'wb') as file_obj:
                download_s3_object_to_file_obj(
                    bucket_name=bucket_name,
                    key=key_name,
                    file_obj=file_obj,
                    access_key_id=access_key_id,
                    secret_access_key=secret_access_key,
                )
            logger.info(f'Download complete: {key_name}, Decrypting')
        except Exception as exc:
            raise ValueError(f'Failed to download S3 object {key_name!r} from bucket {bucket_name!r}: {exc}')

        # decrypt
        try:
            subprocess.check_call(
                ['gpg', '--output', RESTORE_FILE, '--passphrase', preshared_key, '--decrypt', RESTORE_FILE_GPG]
            )

            file_size_in_mb = round(os.stat(RESTORE_FILE).st_size / (BYTES_TO_MEGABYTES), 2)
            logger.info(f'Decrypt Complete: {key_name}. File size: {file_size_in_mb}mb')
        except Exception as exc:
            raise ValueError(f'Failed to decrypt S3 Object {key_name!r} from bucket {bucket_name!r}, bad password?')

        if os.path.exists(RESTORE_FILE_GPG):
            os.unlink(RESTORE_FILE_GPG)

        logger.info(f'Parsing {key_name}')
        with tarfile.open(RESTORE_FILE, 'r:gz') as tar_file:
            for member in tar_file.getmembers():
                try:
                    if member.name.startswith('devices_'):
                        root_master_parse_entities(
                            entity_type=EntityType.Devices,
                            info=tar_file.extractfile(member).read(),
                            backup_source=key_name,
                        )
                    elif member.name.startswith('users_'):
                        root_master_parse_entities(
                            entity_type=EntityType.Users,
                            info=tar_file.extractfile(member).read(),
                            backup_source=key_name,
                        )
                    elif member.name.startswith('raw_devices_'):
                        root_master_parse_entities_raw(
                            entity_type=EntityType.Devices, info=tar_file.extractfile(member).read(),
                        )
                    elif member.name.startswith('raw_users_'):
                        root_master_parse_entities_raw(
                            entity_type=EntityType.Users, info=tar_file.extractfile(member).read(),
                        )
                    elif member.name.startswith('fields_devices_'):
                        root_master_parse_entities_fields(
                            entity_type=EntityType.Devices, info=tar_file.extractfile(member).read(),
                        )
                    elif member.name.startswith('fields_users_'):
                        root_master_parse_entities_fields(
                            entity_type=EntityType.Users, info=tar_file.extractfile(member).read(),
                        )
                    elif member.name.startswith('adapter_client_labels_'):
                        root_master_parse_adapter_client_labels(info=tar_file.extractfile(member).read())
                    else:
                        logger.warning(f'found member {member.name} - no parsing known')
                except Exception:
                    logger.critical(f'Could not parse member {member.name}')

        os.unlink(RESTORE_FILE)

        obj_meta['deleted'] = False
        obj_meta['re_restored'] = re_restored

        # Delete from s3 if necessary
        if delete_backups is True:
            logger.info(f'Deleting key from s3: {key_name!r}')
            try:
                delete_file_from_s3(
                    bucket_name=bucket_name,
                    key_name=key_name,
                    access_key_id=access_key_id,
                    secret_access_key=secret_access_key,
                )
                obj_meta['deleted'] = True
            except Exception:
                logger.exception(f'Could not delete S3 object {key_name!r} from bucket {bucket_name!r}')

        # Set in db as parsed
        if not key_already_parsed:
            root_master_config.insert_one({'type': 'parsed_file', 'key': key_name})
            logger.info(f'Parsing {key_name} complete.')

        return obj_meta
    except Exception:
        logger.exception(f'S3 key download/parse failed: {key_name}')
        raise
    finally:
        restore_cleanup()


def root_master_restore_from_smb():
    """
    Gets an update file of devices & users & fields and loads this to the memory
    """
    # 1. Check if there is enough memory left to parse this
    # 2. Store the file on the disk. Extract it using the preshared key.
    # 3. load each file to the memory, and parse it (Has to be single threaded) while not in a cycle.
    #    This can also be async.
    try:
        root_master_settings = (PluginBase.Instance.feature_flags_config().get(RootMasterNames.root_key) or {})
        # Verify root master settings
        if not root_master_settings.get(RootMasterNames.SMB_enabled):
            raise ValueError(f'Error - Root Master (SMB) mode is not enabled')

        delete_backups = root_master_settings.get(RootMasterNames.delete_backups) or False

        # Check if there is enough space on this machine. Otherwise stop the process
        free_disk_space_in_bytes = get_free_disk_space()
        free_disk_space_in_gb = free_disk_space_in_bytes / (BYTES_TO_GIGABYTES)
        if free_disk_space_in_gb < DISK_SPACE_FREE_GB_MANDATORY:
            message = f'Error - only {free_disk_space_in_gb}gb is left on disk, ' \
                f'while {DISK_SPACE_FREE_GB_MANDATORY} is required'
            raise ValueError(message)

        smb_settings = PluginBase.Instance._smb_settings.copy()

        if not smb_settings.get('enabled'):
            raise ValueError(f'SMB integration is not enabled.')

        if not smb_settings.get('enable_backups'):
            raise ValueError(f'SMB Backups are not enabled.')

        if smb_settings.get('hostname'):
            hostname = smb_settings.get('hostname')
        else:
            raise ValueError(f'SMB hostname is not set.')

        if smb_settings.get('ip'):
            ip = smb_settings.get('ip')
        else:
            raise ValueError(f'SMB IP address is not set.')

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

        smb_client = SMBClient(ip=ip,
                               smb_host=hostname,
                               share_name=share_name,
                               username=smb_settings.get('username') or '',
                               password=smb_settings.get('password') or '',
                               port=smb_settings.get('port'),
                               use_nbns=use_nbns)

        # fetch the existing filenames in the smb share
        files_in_share = smb_client.list_files_on_smb()

        root_master_config = PluginBase.Instance._get_collection('root_master_config', 'core')

        # get a list of all files we haven't parsed yet
        parsed_smb_files = [parsed_file_document['key'] for parsed_file_document
                            in root_master_config.find({'type': 'parsed_file'})]

        # figure out what's new and filter out the '.' files
        new_smb_files = [smb_file for smb_file in files_in_share if files_in_share
                         not in parsed_smb_files and not smb_file.startswith('.')] or []
        logger.info(f'New SMB files found: {",".join(new_smb_files)}')

        # remove any existing restore files
        if os.path.exists(RESTORE_FILE_GPG):
            os.unlink(RESTORE_FILE_GPG)
        if os.path.exists(RESTORE_FILE):
            os.unlink(RESTORE_FILE)

        # For each file, download the file, parse it, set in DB and delete
        for smb_file in new_smb_files:
            try:
                smb_client.download_files_from_smb([smb_file])
                logger.info(f'Download complete: {smb_file}, Decrypting')
            except Exception:
                logger.exception(f'Unable to download {smb_file} from SMB')
                raise

            # decrypt
            try:
                subprocess.check_call([
                    'gpg', '--output', RESTORE_FILE,
                    '--passphrase', preshared_key,
                    '--decrypt', smb_file
                ])
                file_size_in_mb = round(os.stat(RESTORE_FILE).st_size / (BYTES_TO_MEGABYTES), 2)
                logger.info(f'Decrypt Complete: {smb_file}. '
                            f'File size: {file_size_in_mb}mb')
                os.unlink(smb_file)
            except Exception:
                logger.exception(f'Unable to decrypt the file: {smb_file}')
                raise

            try:
                logger.info(f'Parsing {RESTORE_FILE}')
                with tarfile.open(RESTORE_FILE, 'r:gz') as tar_file:
                    for member in tar_file.getmembers():
                        try:
                            if member.name.startswith('devices_'):
                                root_master_parse_entities(
                                    EntityType.Devices, tar_file.extractfile(
                                        member).read(), smb_file
                                )
                            elif member.name.startswith('users_'):
                                root_master_parse_entities(
                                    EntityType.Users, tar_file.extractfile(
                                        member).read(), smb_file
                                )
                            elif member.name.startswith('raw_devices_'):
                                root_master_parse_entities_raw(
                                    EntityType.Devices,
                                    tar_file.extractfile(member).read())
                            elif member.name.startswith('raw_users_'):
                                root_master_parse_entities_raw(
                                    EntityType.Users,
                                    tar_file.extractfile(member).read())
                            elif member.name.startswith('fields_devices_'):
                                root_master_parse_entities_fields(
                                    EntityType.Devices,
                                    tar_file.extractfile(member).read())
                            elif member.name.startswith('fields_users_'):
                                root_master_parse_entities_fields(
                                    EntityType.Users,
                                    tar_file.extractfile(member).read())
                            elif member.name.startswith('adapter_client_labels_'):
                                root_master_parse_adapter_client_labels(
                                    tar_file.extractfile(member).read())
                            else:
                                logger.warning(f'found member {member.name}'
                                               f' - no parsing known')
                        except Exception:
                            logger.exception(f'Could not parse member {member.name}')

                os.unlink(RESTORE_FILE)

                # Delete from share if necessary
                if delete_backups:
                    logger.info(f'Deleting file from SMB share: {smb_file}')
                    try:
                        smb_client.delete_files_from_smb([smb_file])
                    except Exception:
                        logger.exception(f'Could not delete object {smb_file} '
                                         f'from {share_name}')

                # Set in db as parsed
                root_master_config.insert_one({'type': 'parsed_file',
                                               'key': smb_file})
                logger.info(f'Parsing {smb_file} complete.')
            except Exception:
                logger.exception(f'File download/parse failed: {smb_file}')
            finally:
                if os.path.exists(RESTORE_FILE_GPG):
                    os.unlink(RESTORE_FILE_GPG)
                if os.path.exists(RESTORE_FILE):
                    os.unlink(RESTORE_FILE)
    except Exception:
        logger.exception(f'Root Master Mode: Could not restore from SMB')
    finally:
        if os.path.exists(RESTORE_FILE_GPG):
            os.unlink(RESTORE_FILE_GPG)
        if os.path.exists(RESTORE_FILE):
            os.unlink(RESTORE_FILE)

    # this is to provide a value to Flask so it doesn't HTTP 500
    return 0
