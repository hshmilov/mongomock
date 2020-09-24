"""
Handle all root-master architecture functions.
"""
# pylint: disable=too-many-nested-blocks
import logging
import os
import subprocess
import tarfile

from pymongo import ReplaceOne
from pymongo.errors import BulkWriteError

from axonius.modules.central_core import CentralCore
from axonius.utils.json import from_json
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
from axonius.clients.azure.utils import AzureBlobStorageClient

logger = logging.getLogger(f'axonius.{__name__}')
DISK_SPACE_FREE_GB_MANDATORY = 15
BYTES_TO_GIGABYTES = 1024 ** 3
BYTES_TO_MEGABYTES = 1024 ** 2
RESTORE_FILE = 'restore.tar.gz'
RESTORE_FILE_GPG = 'restore.tar.gz.gpg'


def get_central_core_module() -> CentralCore:
    try:
        return get_central_core_module.instance
    except Exception:
        get_central_core_module.instance = CentralCore()

    return get_central_core_module.instance


# pylint: disable=protected-access, too-many-locals, too-many-branches, too-many-statements
def root_master_parse_entities(entity_type: EntityType, info, backup_source=None):
    entities = from_json(info)
    db = get_central_core_module().entity_db_map[entity_type]
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
    entities = from_json(info)
    db = get_central_core_module().raw_adapter_entity_db_map[entity_type]
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
    entities = from_json(info)
    fields_db_map = get_central_core_module().fields_db_map[entity_type]
    for entity in entities:
        entity.pop('_id', None)  # not interesting
        schema_name = entity.get('name')
        plugin_name = entity.get('plugin_name')
        plugin_unique_name = entity.get('plugin_unique_name')
        if schema_name == 'hyperlinks' and plugin_name:
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
        data = from_json(info)
        db = get_central_core_module().adapters_clients_labels_db

        for connection in data:
            client_id = connection.get('client_id')
            node_id = connection.get('node_id')
            plugin_unique_name = connection.get('plugin_unique_name')
            connection.pop('_id', None)

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


def root_master_parse_restore_file(restore_file_identity: str):
    with tarfile.open(RESTORE_FILE, 'r:gz') as tar_file:
        for member in tar_file.getmembers():
            try:
                if member.name.startswith('devices_'):
                    root_master_parse_entities(
                        entity_type=EntityType.Devices,
                        info=tar_file.extractfile(member).read(),
                        backup_source=restore_file_identity,
                    )
                elif member.name.startswith('users_'):
                    root_master_parse_entities(
                        entity_type=EntityType.Users,
                        info=tar_file.extractfile(member).read(),
                        backup_source=restore_file_identity,
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


def verify_available_disk_space():
    disk_free_bytes = get_free_disk_space()
    disk_free_gb = disk_free_bytes / BYTES_TO_GIGABYTES
    disk_free_gb_req = DISK_SPACE_FREE_GB_MANDATORY
    if disk_free_gb <= disk_free_gb_req:
        err = f'Available space must be above {disk_free_gb_req} GB, but only {disk_free_gb} GB is available'
        raise ValueError(err)


def gpg_decrypt_file(preshared_key: str, decrypt_output: str, decrypt_input: str, key_name: str, location: str):
    try:
        subprocess.check_call(
            ['gpg', '--output', decrypt_output, '--passphrase', preshared_key, '--decrypt', decrypt_input]
        )

        file_size_in_mb = round(os.stat(RESTORE_FILE).st_size / BYTES_TO_MEGABYTES, 2)
        logger.info(f'Decrypt Complete: {key_name!r} (location: {location!r}). File size: {file_size_in_mb}mb')
    except Exception as exc:
        raise ValueError(f'Failed to decrypt Object {key_name!r} from location {location!r}, bad password? {str(exc)}')


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

    verify_available_disk_space()


def restore_cleanup():
    """Cleanup all the files used by restore process."""
    if os.path.exists(RESTORE_FILE_GPG):
        os.unlink(RESTORE_FILE_GPG)
    if os.path.exists(RESTORE_FILE):
        os.unlink(RESTORE_FILE)


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
        disk_free_gb = disk_free_bytes / BYTES_TO_GIGABYTES
        obj_bytes = obj_meta['ContentLength']
        obj_gb = obj_bytes / BYTES_TO_GIGABYTES
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
        gpg_decrypt_file(preshared_key, RESTORE_FILE, RESTORE_FILE_GPG, key_name, f's3://{bucket_name}')

        if os.path.exists(RESTORE_FILE_GPG):
            os.unlink(RESTORE_FILE_GPG)

        logger.info(f'Parsing {key_name}')
        root_master_parse_restore_file(key_name)

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
        if not root_master_settings.get(RootMasterNames.enabled):
            raise ValueError(f'Error - Root Master mode is not enabled')

        delete_backups = root_master_settings.get(RootMasterNames.delete_backups) or False

        verify_available_disk_space()

        smb_settings = PluginBase.Instance._smb_settings.copy()

        if not smb_settings.get('enabled'):
            raise ValueError(f'SMB integration is not enabled.')

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
                try:
                    smb_client.download_files_from_smb([smb_file])
                    logger.info(f'Download complete: {smb_file}, Decrypting')
                except Exception:
                    logger.exception(f'Unable to download {smb_file} from SMB')
                    raise

                # decrypt
                gpg_decrypt_file(preshared_key, RESTORE_FILE, smb_file, smb_file, f'smb://{hostname}')
                if os.path.exists(smb_file):
                    os.unlink(smb_file)

                try:
                    logger.info(f'Parsing {RESTORE_FILE}')
                    root_master_parse_restore_file(smb_file)

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
                logger.critical(f'Could not parse restore SMB file {smb_file}', exc_info=True)
    except Exception:
        logger.exception(f'Root Master Mode: Could not restore from SMB')
    finally:
        restore_cleanup()

    # this is to provide a value to Flask so it doesn't HTTP 500
    return 0


def root_master_restore_from_azure():
    """
    Gets an update file of devices & users & fields and loads this to the memory
    """
    # 1. Check if there is enough memory left to parse this
    # 2. Store the file on the disk. Extract it using the preshared key.
    # 3. load each file to the memory, and parse it (Has to be single threaded) while not in a cycle.
    #    This can also be async.
    try:
        root_master_settings = (PluginBase.Instance.feature_flags_config().get(
            RootMasterNames.root_key) or {})
        # Verify root master settings
        if not root_master_settings.get(RootMasterNames.enabled):
            raise ValueError(f'Error - Root Master (Azure) mode is not enabled')

        delete_backups = root_master_settings.get(
            RootMasterNames.delete_backups) or False

        verify_available_disk_space()

        azure_settings = PluginBase.Instance._azure_storage_settings.copy()

        if not azure_settings.get('enabled'):
            raise ValueError(f'Azure integration is not enabled.')

        if azure_settings.get('storage_container_name'):
            storage_container_name = azure_settings.get('storage_container_name')
        else:
            raise ValueError(f'Azure blob storage container name is not set.')

        if azure_settings.get('connection_string'):
            connection_string = azure_settings.get('connection_string')
        else:
            raise ValueError(f'Azure connection string is not set.')

        # Check the PSK to make sure it conforms to known standard/strength
        preshared_key = azure_settings.get('azure_preshared_key')

        # Check the PSK to make sure it conforms to known standard/strength
        if isinstance(preshared_key, str):
            verify_preshared_key(preshared_key)
        else:
            if preshared_key is not None:
                raise ValueError(
                    f'Malformed Azure backup pre-shared key. Expected a '
                    f'str, got {type(preshared_key)}: {str(preshared_key)}')

        try:
            azure_storage_client = AzureBlobStorageClient(
                connection_string=connection_string,
                container_name=storage_container_name
            )
        except Exception:
            logger.exception(f'Unable to create an Azure blob storage client')
            raise

        # fetch the existing filenames in the container
        blobs = list()
        try:
            azure_storage_client.get_blobs(container_name=storage_container_name)
            for blob in azure_storage_client.blobs[storage_container_name]:
                blobs.append(blob.name)
        except BaseException:
            logger.exception(f'Unable to get Azure storage blobs from '
                             f'{storage_container_name}')
            raise

        root_master_config = PluginBase.Instance._get_collection(
            'root_master_config', 'core')

        # get a list of all files we haven't parsed yet
        parsed_smb_files = [parsed_file_document['key'] for parsed_file_document
                            in root_master_config.find({'type': 'parsed_file'})]

        # figure out what's new
        new_azure_files = [blob for blob in blobs if blobs not in parsed_smb_files] or []
        logger.info(f'New Azure files found: {",".join(new_azure_files)}')

        # remove any existing restore files
        if os.path.exists(RESTORE_FILE_GPG):
            os.unlink(RESTORE_FILE_GPG)
        if os.path.exists(RESTORE_FILE):
            os.unlink(RESTORE_FILE)

        # For each file, download the file, parse it, set in DB and delete
        for azure_file in new_azure_files:
            try:
                try:
                    azure_storage_client.block_download_blob(
                        container_name=storage_container_name,
                        blob_name=azure_file)
                    logger.info(f'Download complete: {azure_file}, Decrypting')
                except Exception as err:
                    logger.exception(f'Unable to download {azure_file} from Azure: '
                                     f'{str(err)}')
                    raise

                # decrypt
                gpg_decrypt_file(
                    preshared_key,
                    RESTORE_FILE,
                    azure_file,
                    azure_file,
                    f'azure://{storage_container_name}'
                )

                if os.path.exists(azure_file):
                    os.unlink(azure_file)

                try:
                    logger.info(f'Parsing {RESTORE_FILE}')
                    root_master_parse_restore_file(azure_file)

                    os.unlink(RESTORE_FILE)

                    # Delete from share if necessary
                    if delete_backups:
                        logger.info(f'Deleting {azure_file} from Azure '
                                    f'storage {storage_container_name}')
                        try:
                            azure_storage_client.delete_blob(
                                container_name=storage_container_name,
                                blob_name=azure_file
                            )
                        except Exception as err:
                            logger.exception(f'Could not delete {azure_file} '
                                             f'from {storage_container_name}: '
                                             f'{str(err)}')

                    # Set in db as parsed
                    root_master_config.insert_one({'type': 'parsed_file',
                                                   'key': azure_file})
                    logger.info(f'Parsing of {azure_file} complete.')
                except Exception as err:
                    logger.exception(f'File download/parse failed: {azure_file}: '
                                     f'{str(err)}')
                finally:
                    if os.path.exists(RESTORE_FILE_GPG):
                        os.unlink(RESTORE_FILE_GPG)
                    if os.path.exists(RESTORE_FILE):
                        os.unlink(RESTORE_FILE)
            except Exception:
                logger.critical(f'Could not parse Azure restore key {azure_file}', exc_info=True)
    except Exception as err:
        logger.exception(f'Root Master Mode - Could not restore from Azure: '
                         f'{str(err)}')
    finally:
        restore_cleanup()

    # this is to provide a value to Flask so it doesn't HTTP 500
    return 0
