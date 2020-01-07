"""
Handle all root-master architecture functions.
"""
import json
import logging
import os
import subprocess
import tarfile

from pymongo import ReplaceOne

from axonius.clients.aws.utils import aws_list_s3_objects, download_s3_object_to_file_obj, delete_file_from_s3
from axonius.consts.gui_consts import RootMasterNames
from axonius.entities import EntityType
from axonius.plugin_base import PluginBase
from axonius.utils.host_utils import get_free_disk_space

logger = logging.getLogger(f'axonius.{__name__}')
DISK_SPACE_FREE_GB_MANDATORY = 15
AWS_RESTORE_FILE = 'aws_restore.tar.gz'
AWS_RESTORE_FILE_GPG = 'aws_restore.tar.gz.gpg'


# pylint: disable=protected-access, too-many-locals, too-many-branches, too-many-statements
def root_master_parse_entities(entity_type: EntityType, info):
    entities = json.loads(info)
    db = PluginBase.Instance._entity_db_map[entity_type]
    bulk_replacements = []
    for entity in entities:
        entity.pop('_id', None)  # not interesting
        if 'internal_axon_id' not in entity:
            logger.warning(f'Weird device: {entity}')
            continue
        bulk_replacements.append(
            ReplaceOne(
                {'internal_axon_id': entity['internal_axon_id']},
                entity,
                upsert=True
            )
        )

    db.bulk_write(bulk_replacements)


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
            ReplaceOne(
                {'plugin_unique_name': entity['plugin_unique_name'], 'id': entity['id']},
                entity,
                upsert=True
            )
        )

    db.bulk_write(bulk_replacements)


def root_master_parse_entities_fields(entity_type: EntityType, info):
    entities = json.loads(info)
    fields_db_map = PluginBase.Instance._all_fields_db_map[entity_type]
    for entity in entities:
        entity.pop('_id', None)  # not interesting
        schema_name = entity.get('name')
        plugin_name = entity.get('plugin_name')
        plugin_unique_name = entity.get('plugin_unique_name')
        if schema_name == 'hyperlink' and plugin_name:
            fields_db_map.replace_one(
                {
                    'name': schema_name,
                    'plugin_name': plugin_name
                },
                entity,
                upsert=True
            )
        elif schema_name in ['parsed', 'dynamic']:
            if plugin_unique_name:
                current_db_items = (fields_db_map.find_one(
                    {
                        'name': schema_name,
                        'plugin_unique_name': plugin_unique_name
                    }
                ) or {}).get('items') or []

                new_schema = entity.get('items') or []
                new_names = [field['name'] for field in new_schema]

                for current_item in current_db_items:
                    if current_item['name'] not in new_names:
                        new_schema.append(current_item)

                fields_db_map.update_one(
                    {
                        'name': schema_name,
                        'plugin_unique_name': plugin_unique_name
                    },
                    {
                        '$set': {
                            'schema': {'items': new_schema}
                        }
                    },
                    upsert=True
                )
        elif schema_name in ['exist', 'raw']:
            field_name = {
                'exist': 'fields',
                'raw': 'raw'
            }[schema_name]
            exist_fields = entity.get(field_name) or []
            if exist_fields and plugin_unique_name:
                fields_db_map.update_one(
                    {
                        'name': schema_name,
                        'plugin_unique_name': plugin_unique_name
                    },
                    {
                        '$addToSet': {
                            field_name: {
                                '$each': exist_fields
                            }
                        }
                    },
                    upsert=True
                )


# pytest: disable=protected-access
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
        root_master_settings = (PluginBase.Instance.feature_flags_config().get(RootMasterNames.root_key) or {})
        # Verify root master settings
        if not root_master_settings.get(RootMasterNames.enabled):
            raise ValueError(f'Error - root master mode is not enabled')
        delete_backups = root_master_settings.get(RootMasterNames.delete_backups) or False

        aws_s3_settings = PluginBase.Instance._aws_s3_settings.copy()
        # Verify s3 settings
        if not aws_s3_settings.get('enabled'):
            raise ValueError(f'S3 Settings is not enabled')

        aws_access_key_id = aws_s3_settings.get('aws_access_key_id')
        aws_secret_access_key = aws_s3_settings.get('aws_secret_access_key')
        aws_bucket_name = aws_s3_settings.get('bucket_name')
        preshared_key = aws_s3_settings.get('preshared_key')

        if (aws_access_key_id and not aws_secret_access_key) or (aws_secret_access_key and not aws_access_key_id):
            raise ValueError(f'AWS access key id / secret access key - Both or None should exist')

        if not aws_bucket_name:
            raise ValueError(f'Bucket name does not exist')

        # Check if there is enough space on this machine. Otherwise stop the process
        free_disk_space_in_bytes = get_free_disk_space()
        free_disk_space_in_gb = free_disk_space_in_bytes / (1024 ** 3)
        if free_disk_space_in_gb < DISK_SPACE_FREE_GB_MANDATORY:
            message = f'Error - only {free_disk_space_in_gb}gb is left on disk, ' \
                f'while {DISK_SPACE_FREE_GB_MANDATORY} is required'
            raise ValueError(message)

        # Now when we have all settings configured, we can start the process.
        # First, get the list of all keys in the s3 bucket
        s3_keys = []
        for s3_object in aws_list_s3_objects(
                bucket_name=aws_bucket_name,
                access_key_id=aws_access_key_id,
                secret_access_key=aws_secret_access_key
        ):
            if s3_object['Size'] * 2 > free_disk_space_in_bytes:
                # we require two times the size because we also need to gpg-decrypt this file.
                logger.error(f'Not parsing S3 Object {s3_object}, not enough disk space (required two times the size)')
                continue
            s3_keys.append(s3_object['Key'])

        # Next, get the list of all files we haven't parsed yet.
        root_master_config = PluginBase.Instance._get_collection('root_master_config', 'core')
        parsed_s3_keys = []
        for parsed_file_document in root_master_config.find({'type': 'parsed_file'}):
            parsed_s3_keys.append(parsed_file_document['key'])

        # Calculate what's new
        new_s3_keys = [file_key for file_key in s3_keys if file_key not in parsed_s3_keys]
        logger.info(f'New S3 keys found: {",".join(new_s3_keys)}')

        # For each file, download the file, parse it, set in DB and delete
        if os.path.exists(AWS_RESTORE_FILE_GPG):
            os.unlink(AWS_RESTORE_FILE_GPG)
        if os.path.exists(AWS_RESTORE_FILE):
            os.unlink(AWS_RESTORE_FILE)
        for s3_key in new_s3_keys:
            try:
                logger.info(f'Downloading backup file: {s3_key}')
                with open(AWS_RESTORE_FILE_GPG, 'wb') as file_obj:
                    download_s3_object_to_file_obj(
                        aws_bucket_name,
                        s3_key,
                        file_obj,
                        access_key_id=aws_access_key_id,
                        secret_access_key=aws_secret_access_key,
                    )
                logger.info(f'Download complete: {s3_key}, Decrypting')

                # Encrypt
                subprocess.check_call([
                    'gpg', '--output', AWS_RESTORE_FILE,
                    '--passphrase', preshared_key,
                    '--decrypt', AWS_RESTORE_FILE_GPG
                ])

                file_size_in_mb = round(os.stat(AWS_RESTORE_FILE).st_size / (1024 ** 2), 2)
                logger.info(f'Decrypt Complete: {s3_key}. File size: {file_size_in_mb}mb')
                os.unlink(AWS_RESTORE_FILE_GPG)

                logger.info(f'Parsing {s3_key}')
                with tarfile.open(AWS_RESTORE_FILE, 'r:gz') as tar_file:
                    for member in tar_file.getmembers():
                        try:
                            if member.name.startswith('devices_'):
                                root_master_parse_entities(EntityType.Devices, tar_file.extractfile(member).read())
                            elif member.name.startswith('users_'):
                                root_master_parse_entities(EntityType.Users, tar_file.extractfile(member).read())
                            elif member.name.startswith('raw_devices_'):
                                root_master_parse_entities_raw(EntityType.Devices, tar_file.extractfile(member).read())
                            elif member.name.startswith('raw_users_'):
                                root_master_parse_entities_raw(EntityType.Users, tar_file.extractfile(member).read())
                            elif member.name.startswith('fields_devices_'):
                                root_master_parse_entities_fields(EntityType.Devices,
                                                                  tar_file.extractfile(member).read())
                            elif member.name.startswith('fields_users_'):
                                root_master_parse_entities_fields(EntityType.Users, tar_file.extractfile(member).read())
                            else:
                                logger.warning(f'found member {member.name} - no parsing known')
                        except Exception:
                            logger.exception(f'Could not parse member {member.name}')
                os.unlink(AWS_RESTORE_FILE)
                # Delete from s3 if necessary
                if delete_backups:
                    logger.info(f'Deleting key from s3: {s3_key}')
                    try:
                        delete_file_from_s3(
                            aws_bucket_name,
                            s3_key,
                            access_key_id=aws_access_key_id,
                            secret_access_key=aws_secret_access_key
                        )
                    except Exception:
                        logger.exception(f'Could not delete object {s3_key} from bucket {aws_bucket_name}')

                # Set in db as parsed
                root_master_config.insert_one({'type': 'parsed_file', 'key': s3_key})
                logger.info(f'Parsing {s3_key} complete.')
            except Exception:
                logger.exception(f'S3 key download/parse failed: {s3_key}')
            finally:
                if os.path.exists(AWS_RESTORE_FILE_GPG):
                    os.unlink(AWS_RESTORE_FILE_GPG)
                if os.path.exists(AWS_RESTORE_FILE):
                    os.unlink(AWS_RESTORE_FILE)
    except Exception:
        logger.exception(f'Root Master Mode: Could not restore from s3')
    finally:
        if os.path.exists(AWS_RESTORE_FILE_GPG):
            os.unlink(AWS_RESTORE_FILE_GPG)
        if os.path.exists(AWS_RESTORE_FILE):
            os.unlink(AWS_RESTORE_FILE)
