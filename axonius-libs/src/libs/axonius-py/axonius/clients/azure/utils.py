import datetime
import logging
import re
from pathlib import Path

# pylint: disable=no-name-in-module,import-error
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from azure.core.paging import ItemPaged
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient, \
    ContainerEncryptionScope, LeaseProperties, ContainerProperties, \
    CopyProperties, ContentSettings, BlobProperties
# pylint: enable=no-name-in-module,import-error

from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import parse_bool_from_raw, int_or_none

logger = logging.getLogger(f'axonius.{__name__}')

# this pattern checks to see that the container is named per microsoft's reqs
CONTAINER_NAME_PATTERN = r'^[a-z0-9]{1}((?!\-\-)[a-z0-9-]){3,63}$'


class AzureBlobCopyData(SmartJsonClass):
    """ This class captures all data about an Azure blob's copy status """
    copy_id = Field(str, 'Copy Data ID')
    source = Field(str, 'Source')
    status = Field(str, 'Status')
    progress = Field(str, 'Progress')
    completion_time = Field(datetime.datetime, 'Completion Time')
    status_description = Field(str, 'Status Description')
    incremental_copy = Field(str, 'Incremental Copy')
    destination_snapshot = Field(datetime.datetime, 'Destination Snapshot')


class AzureBlobContentSettings(SmartJsonClass):
    """ This class captures all data around the Azure blob content settings """
    content_type = Field(str, 'Content Type')
    content_encoding = Field(str, 'Encoding')
    content_language = Field(str, 'Language')
    content_md5 = Field(str, 'MD5')
    content_disposition = Field(str, 'Disposition')
    cache_control = Field(str, 'Cache Control')


class AzureBlobLease(SmartJsonClass):
    """ This class captures all data around an Azure blob lease """
    status = Field(str, 'Status')
    state = Field(str, 'State')
    duration = Field(int, 'Duration')
    blob_tier = Field(str, 'Blob Tier')
    blob_tier_change_time = Field(datetime.datetime, 'Change Time')
    blob_tier_inferred = Field(str, 'Inferred Tier')
    deleted = Field(bool, 'Deleted')
    deleted_time = Field(datetime.datetime, 'Deleted Time')
    remaining_retention_days = Field(str, 'Remaining Retention Days')
    creation_time = Field(datetime.datetime, 'Creation Time')
    archive_status = Field(str, 'Archive Status')
    encryption_key_sha256 = Field(str, 'Encryption Key')
    encryption_scope = Field(str, 'Encryption Scope')
    request_server_encrypted = Field(str, 'Server Encrypted')


class AzureBlob(SmartJsonClass):
    """ This class captures all information about an Azure blob. """
    name = Field(str, 'Name')
    container = Field(str, 'Container')
    snapshot = Field(str, 'Snapshot')
    blob_type = Field(str, 'Blob Type')
    metadata = Field(dict, 'Metadata')
    last_modified = Field(datetime.datetime, 'Last Modified')
    etag = Field(str, 'ETag')
    size = Field(int, 'Size')
    content_range = Field(str, 'Content Range')
    committed_block_count = Field(int, 'Committed Block Count')
    page_blob_sequence_number = Field(int, 'Page Blob Sequence Number')
    server_encrypted = Field(bool, 'Server-Encrypted')
    copy = Field(AzureBlobCopyData, 'Copy Data')
    content_settings = Field(AzureBlobContentSettings, 'Content Settings')
    lease = Field(AzureBlobLease, 'Lease Information')
    blob_tier = Field(str, 'Blob Tier')
    blob_tier_change_time = Field(datetime.datetime, 'Tier Changed')
    blob_tier_inferred = Field(bool, 'Tier Inferred')
    deleted = Field(bool, 'Deleted')
    deleted_time = Field(datetime.datetime, 'Deleted Time')
    remaining_retention_days = Field(int, 'Remaining Retention Days')
    creation_time = Field(datetime.datetime, 'Creation Time')
    archive_status = Field(str, 'Archive Status')
    encryption_key_sha256 = Field(str, 'Encryption Key')
    encryption_scope = Field(str, 'Encryption Scope')
    request_server_encrypted = Field(bool, 'Request Server Encrypted')


class AzureBlobContainer(SmartJsonClass):
    """ This class maintains information about a single blob container """
    name = Field(str, 'Name')
    last_modified = Field(datetime.datetime, 'Last Modified')
    etag = Field(str, 'ETag')
    lease = Field(AzureBlobLease, 'Lease')
    public_access = Field(str, 'Public Access')
    has_immutability_policy = Field(bool, 'Immutability Policy')
    has_legal_hold = Field(bool, 'Legal Hold')
    metadata = Field(dict, 'Metadata')
    default_encryption_scope = Field(str, 'Default Encryption Scope')
    encryption_scope_override = Field(bool, 'Encryption Scope Override')


class AzureBlobStorageClient:
    def __init__(self, connection_string: str, container_name: str = None):
        """
        This is the primary class for holding Azure blob storage information
        and the connection client. The *connection_string is maintained as a
        private attribute, since it contains sensitive information (essentially
        the api_token), while the other attributes are public in nature due to
        their utility.

        NOTE:
        There are other ways to build the blob service client, so this is to
        support additions in the future (i.e. custom connection strings using
        a default protocol, account name and account key)

        :param connection_string: The authentication information used to build
        the clients.
        :param container_name: [Optional] The name of the container to use, if
        you would like to also create a container client upon instantiation.
        """
        if connection_string and isinstance(connection_string, str):
            self.__connection_string = connection_string
            try:
                self.blob_service_client = self._get_blob_service_client_by_connection_string()
            except Exception as err:
                logger.exception(f'Unable to create an Azure blob service '
                                 f'client: {str(err)}')
                raise
        else:
            raise ValueError(f'Malformed connection string. Expected a string, '
                             f'got {type(connection_string)}: '
                             f'{str(connection_string)}')

        # if passed, we can setup the container client to save some time
        if container_name and isinstance(container_name, str) and \
                re.match(CONTAINER_NAME_PATTERN, container_name):
            self.container_name = container_name
            try:
                self.container_client = self._get_container_client(
                    container_name=container_name)
            except Exception as err:
                logger.exception(f'Unable to create an Azure container client: '
                                 f'{str(err)}')
        else:
            if container_name is not None:
                logger.warning(f'Malformed container name. Expected a string, '
                               f'got {type(container_name)}: '
                               f'{str(container_name)}')
            self.container_name = None
            self.container_client = None

        self.blob_containers = set()
        self.blobs = dict()

    def _get_blob_service_client_by_connection_string(self) -> BlobServiceClient:
        """ Create a blob service client using a connection string """
        client = None
        try:
            blob_service_client = BlobServiceClient.from_connection_string(
                self.__connection_string)
            if isinstance(blob_service_client, BlobServiceClient):
                client = blob_service_client
            else:
                logger.error(f'Malformed Azure blob service client. Expected a '
                             f'BlobServiceClient, got {type(blob_service_client)}'
                             f': {str(blob_service_client)}')
        except Exception as err:
            logger.exception(f'Azure blob service client creation failed:'
                             f'{err}')
            raise

        return client

    # pylint: disable=invalid-triple-quote
    def _get_container_client(self, container_name: str) -> ContainerClient:
        """
        Create an Azure container client, which will be saved as a
        class attribute.

        :param container_name: The name of the container to use
        """
        client = None
        if re.match(CONTAINER_NAME_PATTERN, container_name):
            if isinstance(self.blob_service_client, BlobServiceClient):
                try:
                    container_client = self.blob_service_client.get_container_client(
                        container=container_name)
                    if isinstance(container_client, ContainerClient):  # pylint: disable=no-else-return
                        self.container_client = container_client
                        client = container_client
                    else:
                        logger.warning(
                            f'Malformed Azure container client. Expected a '
                            f'ContainerClient, got {type(container_client)}: '
                            f'{str(container_client)}')
                except Exception as err:
                    logger.exception(
                        f'Unable to get an Azure container client: {err}')
            else:
                logger.error(
                    f'Malformed or non-existent Azure blob service client. '
                    f'Expected a BlobServiceClient, got '
                    f'{type(self.blob_service_client)}: '
                    f'{str(self.blob_service_client)}')
        else:
            logger.warning(
                f'The container name may only contain lowercase '
                f'letters, numbers, and hyphens, and must begin with a letter '
                f'or a number. Each hyphen must be preceded and followed by a '
                f'non-hyphen character. The name must also be between 3 and 63 '
                f'characters long: {str(container_name)}')

        return client

    def create_blob_container(self, container_name: str) -> bool:
        """
        Create a new container for blob storage

        :param container_name: The name of the container to use
        :return: A success/failure indicator
        """
        if re.match(CONTAINER_NAME_PATTERN, container_name):
            try:
                if not self.container_client or self.container_name != container_name:
                    try:
                        self.container_client = self._get_container_client(container_name)
                        self.container_name = container_name
                    except Exception:
                        logger.exception(f'Unable to acquire an Azure container '
                                         f'client to create a blob container')
                        raise

                if isinstance(self.container_client, ContainerClient):
                    try:
                        self.container_client.create_container()
                        # update the blob_containers attribute
                        self.get_blob_containers()
                        return True
                    except ResourceExistsError as err:
                        # no harm, no foul -- making this INFO
                        logger.info(f'Blob container {container_name} already '
                                    f'exists {err.reason}')
                        return True
                    except Exception as err:
                        logger.exception(
                            f'Failed to create the blob container '
                            f'({container_name}): {err}')
                        return False
                else:
                    logger.warning(
                        f'Malformed Azure container client. Expected a '
                        f'ContainerClient object, got {type(self.container_client)}: '
                        f'{str(self.container_client)}')
                    return False
            except Exception:
                logger.exception(f'Unable to create a blob container ({container_name})')
                return False
        else:
            logger.warning(
                f'The container name may only contain lowercase '
                f'letters, numbers, and hyphens, and must begin with a letter '
                f'or a number. Each hyphen must be preceded and followed by a '
                f'non-hyphen character. The name must also be between 3 and 63 '
                f'characters long: {str(container_name)}')

        return False

    def delete_blob(self, container_name: str, blob_name: str) -> bool:
        """
        Deletes the given *blob_name from the given *container_name.

        :param container_name: The name of the container that contains the blob.
        :param blob_name: The name of the blob to be deleted.
        :return: A success/failure indicator as a boolean
        """
        try:
            if not self.container_client or self.container_name != container_name:
                try:
                    self.container_client = self._get_container_client(container_name)
                except Exception:
                    logger.exception(
                        f'Unable to acquire an Azure container client '
                        f'to create a blob container')
                    raise

            if isinstance(self.container_client, ContainerClient):
                # create a blob client
                blob_client = self.container_client.get_blob_client(blob_name)
                if isinstance(blob_client, BlobClient):
                    try:
                        blob_client.delete_blob()
                        return True
                    except ResourceNotFoundError as err:
                        logger.warning(
                            f'The blob ({blob_name}) was not found. '
                            f'{err.reason}:')
                        return False
                    except Exception as err:
                        logger.warning(f'Failed to delete the blob ({blob_name}) '
                                       f'from {container_name}: {err}')
                        return False
                else:
                    logger.warning(f'Malformed Azure blob client. Expected a '
                                   f'BlobClient object, got {type(blob_client)}:'
                                   f' {str(blob_client)}')
                    return False
            else:
                logger.warning(
                    f'Malformed Azure container client. Expected a '
                    f'ContainerClient object, got {type(self.container_client)}: '
                    f'{str(self.container_client)}')
                return False
        except Exception as err:
            logger.exception(f'Unable to delete the blob ({blob_name}): {str(err)}')

        return False

    def delete_blob_container(self, container_name: str) -> bool:
        """
        Delete a given blob container by its *container_name. This action is
        not reversible.

        :param container_name: The container name that you would like to remove.
        :return: A success/failure indicator as a boolean
        """
        try:
            if not self.container_client or self.container_name != container_name:
                try:
                    self.container_client = self._get_container_client(container_name)
                except Exception:
                    logger.exception(
                        f'Unable to acquire an Azure container client '
                        f'to create a blob container')
                    raise

            if isinstance(self.container_client, ContainerClient):
                try:
                    self.container_client.delete_container()
                    # update the blob containers attribute
                    self.get_blob_containers()
                    return True
                except ResourceNotFoundError as err:
                    logger.warning(
                        f'The container ({container_name}) was not found. '
                        f'{err.reason}:')
                    return True
                except Exception as err:
                    logger.exception(f'Failed to delete the blob container '
                                     f'({container_name}): {err}')
                    return False
            else:
                logger.warning(
                    f'Malformed Azure container client. Expected a '
                    f'ContainerClient object, got {type(self.container_client)}: '
                    f'{str(self.container_client)}')
                return False
        except Exception as err:
            logger.exception(f'Unable to delete the container '
                             f'({container_name}): {str(err)}')
        return False

    # pylint: disable=too-many-nested-blocks, too-many-branches
    def get_blob_containers(self):
        """ List all blob containers and update the instance attribute. """
        self.blob_containers = set()
        try:
            if not self.blob_service_client:
                try:
                    self.blob_service_client = BlobServiceClient.from_connection_string(
                        self.__connection_string)
                except Exception as err:
                    logger.exception(f'Unable to get an Azure blob service '
                                     f'client: {err}')
                    raise

            if isinstance(self.blob_service_client, BlobServiceClient):
                try:
                    list_response = self.blob_service_client.list_containers()
                    if isinstance(list_response, ItemPaged):
                        for response in list_response:
                            if isinstance(response, ContainerProperties):
                                scope = response.get('encryption_scope')
                                if isinstance(scope, ContainerEncryptionScope):
                                    encryption_scope = scope.default_encryption_scope
                                    encryption_scope_override = scope.prevent_encryption_scope_override
                                else:
                                    encryption_scope = None
                                    encryption_scope_override = None

                                blob_container = AzureBlobContainer(
                                    name=response.get('name'),
                                    last_modified=parse_date(response.get('last_modified')),
                                    etag=response.get('etag'),
                                    lease=parse_lease(response.get('lease')),
                                    public_access=response.get('public_access'),
                                    has_immutability_policy=parse_bool_from_raw(
                                        response.get('has_immutability_policy')),
                                    has_legal_hold=parse_bool_from_raw(response.get('has_legal_hold')),
                                    metadata=response.get('metadata'),
                                    default_encryption_scope=encryption_scope,
                                    encryption_scope_override=parse_bool_from_raw(encryption_scope_override)
                                )
                                self.blob_containers.add(blob_container)
                            else:
                                logger.warning(
                                    f'Malformed response to list containers. '
                                    f'Expected a dict, got {type(response)}: '
                                    f'{str(response)}')
                    else:
                        logger.warning(
                            f'Malformed list response. Expected an ItemPaged '
                            f'object, got {type(list_response)}: '
                            f'{str(list_response)}')
                except Exception as err:
                    logger.exception(f'Unable to get an Azure container client: {err}')
                    raise
            else:
                raise ValueError(
                    f'Malformed Azure blob service client. Expected a '
                    f'BlobServiceClient, got {type(self.blob_service_client)}: '
                    f'{str(self.blob_service_client)}')
        except Exception as err:
            logger.exception(f'Failed to retrieve the container list: {err}')

    def get_blobs(self, container_name: str):
        """
        List all of the blobs in a given container and save them as
        AzureBlob class instances inside the main AzureBlobStorageClient class
        instance. To see them call to self.blobs[container_name].

        :param container_name: The container name that you would like to remove.
        """
        self.blobs[container_name] = list()
        try:
            if not self.container_client or self.container_name != container_name:
                try:
                    self.container_client = self._get_container_client(container_name)
                except Exception:
                    logger.exception(f'Unable to acquire an Azure container '
                                     f'client to create a blob container')
                    raise

            if isinstance(self.container_client, ContainerClient):
                try:
                    list_response = self.container_client.list_blobs()
                    if isinstance(list_response, ItemPaged):
                        for response in list_response:
                            if isinstance(response, BlobProperties):
                                blob = AzureBlob(
                                    name=response.get('name'),
                                    container=response.get('container'),
                                    snapshot=response.get('snapshot'),
                                    blob_type=response.get('blob_type'),
                                    metadata=response.get('metadata'),
                                    last_modified=parse_date(response.get('last_modified')),
                                    etag=response.get('etag'),
                                    size=int_or_none(response.get('size')),
                                    content_range=response.get('content_range'),
                                    committed_block_count=int_or_none(
                                        response.get('append_blob_committed_block_count')),
                                    page_blob_sequence_number=int_or_none(response.get('page_blob_sequence_number')),
                                    server_encrypted=parse_bool_from_raw(response.get('server_encrypted')),
                                    copy=parse_copy_data(response.get('copy')),
                                    content_settings=parse_content_settings(response.get('content_settings')),
                                    lease=parse_lease(response.get('lease')),
                                    blob_tier=response.get('blob_tier'),
                                    blob_tier_change_time=parse_date(response.get('blob_tier_change_time')),
                                    blob_tier_inferred=parse_bool_from_raw(response.get('blob_tier_inferred')),
                                    deleted=parse_bool_from_raw(response.get('deleted')),
                                    deleted_time=parse_date(response.get('deleted_time')),
                                    remaining_retention_days=int_or_none(response.get('remaining_retention_days')),
                                    creation_time=parse_date(response.get('creation_time')),
                                    archive_status=response.get('archive_status'),
                                    encryption_key_sha256=response.get('encryption_key_sha256'),
                                    encryption_scope=response.get('encryption_scope'),
                                    request_server_encrypted=parse_bool_from_raw(
                                        response.get('request_server_encrypted'))
                                )
                                self.blobs[container_name].append(blob)
                            else:
                                logger.warning(f'Malformed response in the list '
                                               f'response. Expected a dict, got '
                                               f'{type(response)}: {str(response)}')
                    else:
                        logger.warning(
                            f'Malformed response while listing blobs. Expected '
                            f'an ItemPaged object, got {type(list_response)}:'
                            f'{str(list_response)}')
                except ResourceNotFoundError as err:
                    logger.warning(f'The container ({container_name}) was not '
                                   f'found: {err.reason}')
                except Exception as err:
                    logger.exception(f'Failed to list the blob containers '
                                     f'({list_response}): {err}')
            else:
                logger.warning(
                    f'Malformed ContainerClient. Got a '
                    f'{type(self.container_client)}: {str(self.container_client)}')
        except Exception:
            logger.exception(f'Unable to list blobs in {container_name}')

    def block_upload_blob(self, container_name: str, blob_name: str, blob_path: str = None) -> bool:
        """
        Upload a blob to the passed container.

        :param container_name: The name of the container that contains the
        desired blob.
        :param blob_name: The name of the blob to be downloaded.
        :return: A success/failure indicator as a boolean
        """
        # create a new service client using a connection string
        try:
            if not self.container_client or self.container_name != container_name:
                try:
                    self.container_client = self._get_container_client(container_name)
                except Exception:
                    logger.exception(f'Unable to acquire an Azure container '
                                     f'client to create a blob container')
                    raise

            if isinstance(self.container_client, ContainerClient):
                blob_client = self.container_client.get_blob_client(blob_name)
                if isinstance(blob_client, BlobClient):
                    try:
                        blob_file = Path(blob_path) if blob_path else blob_name
                        with open(blob_file, 'rb') as data:
                            blob_client.upload_blob(data, blob_type='BlockBlob')

                        # rebuild the blob listing
                        self.blobs[container_name] = list()
                        self.get_blobs(container_name)
                        return True
                    except ResourceExistsError:
                        logger.exception(
                            f'Blob ({blob_name}) already exists in '
                            f'{container_name}')
                        return False
                    except Exception as err:
                        logger.exception(
                            f'Failed to perform block upload of blob '
                            f'({blob_name}): {err}')
                        return False
                else:
                    logger.warning(f'Malformed Azure blob client. Expected a '
                                   f'BlobClient, got {type(blob_client)}, '
                                   f'{str(blob_client)}')
                    return False
            else:
                logger.warning(f'Malformed Azure container client. Expected a '
                               f'ContainerClient, got {type(self.container_client)}:'
                               f'{str(self.container_client)}')
                return False
        except Exception:
            logger.exception(f'Unable to upload {blob_name} to {container_name}')
            return False

    def block_download_blob(self, container_name: str, blob_name: str):
        """
        Download a blob from the specified container.

        NOTE: This function does not check for the existence of any file on the
        target system and will overwrite any existing local file.

        :param container_name: The name of the container that contains the
        desired blob.
        :param blob_name: The name of the blob to be downloaded.
        """
        try:
            if not self.container_client or self.container_name != container_name:
                try:
                    self.container_client = self._get_container_client(container_name)
                except Exception:
                    logger.exception(f'Unable to acquire an Azure container '
                                     f'client to create a blob container')
                    raise

            if isinstance(self.container_client, ContainerClient):
                try:
                    blob_client = self.container_client.get_blob_client(blob_name)
                except Exception as err:
                    logger.exception(f'Unable to get an Azure blob client: {err}')
                    raise

                try:
                    with open(blob_name, 'wb') as data:
                        download_stream = blob_client.download_blob()
                        data.write(download_stream.readall())
                except Exception as err:
                    logger.exception(f'Unable to stream {blob_name}: {err}')
                    raise
            else:
                logger.warning(
                    f'Malformed Azure container client. Expected a '
                    f'ContainerClient, got {type(self.container_client)}:'
                    f'{str(self.container_client)}')
        except Exception:
            logger.exception(f'Unable to download {blob_name} from {container_name}')
            raise


def parse_copy_data(copy_data: CopyProperties) -> AzureBlobCopyData:
    data = AzureBlobCopyData(
        copy_id=copy_data.get('id'),
        source=copy_data.get('source'),
        status=copy_data.get('status'),
        progress=copy_data.get('progress'),
        completion_time=parse_date(copy_data.get('completion_time')),
        status_description=copy_data.get('status_description'),
        incremental_copy=parse_bool_from_raw(copy_data.get('incremental_copy')),
        destination_snapshot=parse_date(copy_data.get('destination_snapshot'))
    )
    return data


def parse_content_settings(settings: ContentSettings) -> AzureBlobContentSettings:
    content_settings = AzureBlobContentSettings(
        content_type=settings.get('content_type'),
        content_encoding=settings.get('content_encoding'),
        content_language=settings.get('content_language'),
        content_md5=settings.get('content_md5'),
        content_disposition=settings.get('content_disposition'),
        cache_control=settings.get('cache_control')
    )
    return content_settings


def parse_lease(lease: LeaseProperties) -> AzureBlobLease:
    lease_data = AzureBlobLease(
        status=lease.get('status'),
        state=lease.get('state'),
        duration=int_or_none(lease.get('duration')),
        blob_tier=lease.get('blob_tier'),
        blob_tier_change_time=parse_date(lease.get('blob_tier_change_time')),
        blob_tier_inferred=lease.get('blob_tier_inferred'),
        deleted=parse_bool_from_raw(lease.get('deleted')),
        deleted_time=parse_date(lease.get('deleted_time')),
        remaining_retention_days=lease.get('remaining_retention_days'),
        creation_time=parse_date(lease.get('creation_time')),
        archive_status=lease.get('archive_status'),
        encryption_key_sha256=lease.get('encryption_key_sha256'),
        encryption_scope=lease.get('encryption_scope'),
        request_server_encrypted=lease.get('request_server_encrypted')
    )
    return lease_data
