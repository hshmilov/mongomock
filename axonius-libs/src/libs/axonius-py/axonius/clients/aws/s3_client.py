import datetime
import functools
import json
import logging
from time import strftime

import boto3

from axonius.clients.aws.aws_clients import get_paginated_continuation_token_api

logger = logging.getLogger(f'axonius.{__name__}')

BUCKET_ACL = ['private', 'public-read', 'public-read-write', 'authenticated-read']
OBJECT_STORAGE_CLASS = ['STANDARD', 'REDUCED_REDUNDANCY', 'STANDARD_IA',
                        'ONEZONE_IA', 'INTELLIGENT_TIERING', 'GLACIER', 'DEEP_ARCHIVE']
STRFTIME_FORMAT = '%Y-%m-%d-%H-%M-%S'


class S3Client:  # pylint: disable=too-many-instance-attributes
    def __init__(self,
                 access_key: str = None,
                 secret_key: str = None,
                 region: str = 'us-east-1',
                 use_instance_role: bool = False,
                 config: dict = None,
                 session_token: str = None,
                 use_ssl: bool = True,
                 verify: bool = True
                 ):
        self.__session_token = session_token
        self._use_ssl = use_ssl
        self._verify = verify
        self._config = config
        self.buckets = list()

        self._use_instance_role = use_instance_role
        self._set_credentials(access_key, secret_key, session_token)

        self.regions = self.get_available_regions()
        self.region = region if region in self.regions else None

        self.client = self.create_client()

    @property
    def access_key(self) -> str:
        """
        Obfuscate the somewhat sensitive AWS access key ID by return the
        initial 4 characters, 12 asterisks and the final 4 characters
        (ex. ATEF************BD7H). This is used primarily in the logger.
        """
        return f'{self._access_key[:4]}{"*"*12}{self._access_key[-4:]}'

    def _set_credentials(self,
                         access_key: str,
                         secret_key: str,
                         session_token: str = None):
        """
        Set the AWS credentials appropriate to the permission type. If using
        an instance role, zero the secret/access keys. Otherwise, save and
        protect the secrets (as best as python can).

        :param access_key: The AWS Acess Key ID as a string
        :param secret_key: The AWS Secret Key as a string
        :param session_token: [Optional] An AWS session token. This must
        be manually refreshed or use RefreshableCredentials.
        """
        if self._use_instance_role:
            self._access_key = None
            self.__secret_key = None
            self.__session_token = None
        else:
            if not access_key and not secret_key:
                raise ValueError(f'AWS access and secret not found and not '
                                 f'using EC2 instance role')

            self._access_key = access_key
            self.__secret_key = secret_key
            self.__session_token = session_token

    def create_client(self):
        """ Build an S3 client object """
        try:
            return boto3.client(service_name='s3',
                                aws_access_key_id=self._access_key,
                                aws_secret_access_key=self.__secret_key,
                                aws_session_token=self.__session_token,
                                region_name=self.region,
                                use_ssl=self._use_ssl,
                                verify=self._verify,
                                config=self._config
                                )
        except Exception:
            logger.exception(f'Unable to create an S3 client using '
                             f'{self.access_key}')

    # pylint: disable=invalid-triple-quote
    def list_buckets(self):
        """
        Save as a list in an attribute all of the buckets that are visible
        to this S3 client.

        REQUIRES:
            s3:ListBucket
            s3:HeadBucket
            s3:ListAllMyBuckets
        """
        self.buckets = list()
        try:
            buckets_dict = self.client.list_buckets()
            if isinstance(buckets_dict, dict):
                buckets = buckets_dict.get('Buckets')
                if isinstance(buckets, list):
                    self.buckets = [bucket.get('Name') for bucket in buckets]
                else:
                    logger.warning(f'Malformed buckets. Expected a list, got '
                                   f'{type(buckets)}: {str(buckets)}')
            else:
                logger.warning(f'Malformed list buckets response. Expected a '
                               f'dict, got {type(buckets_dict)}: '
                               f'{str(buckets_dict)}')
        except Exception as err:
            logger.exception(f'Unable to list buckets for {self.access_key}: '
                             f'{str(err)}')

    def create_bucket(self, bucket_name: str, region: str = 'us-east-1', acl: str = ''):
        """
        Create a new S3 bucket and update the buckets attribute with the
        list of buckets.

        REQUIRES:
            s3:CreateBucket
            s3:HeadBucket
            s3:ListBucket

        :param bucket_name: The name of the new bucket as a string.
        :param region: The desired region for the bucket as a string
        :param acl: The canned ACL (any one of the options from BUCKET_ACL)
        as a string
        """
        bucket_name = self.prepare_name(bucket_name)
        try:
            if region == 'us-east-1':
                try:
                    response = self.client.create_bucket(
                        ACL=acl if acl in BUCKET_ACL else 'private',
                        Bucket=bucket_name,
                    )
                except Exception as err:
                    logger.exception(
                        f'Unable to create S3 bucket ({bucket_name}) using '
                        f'{self.access_key}: {str(err)}')

            elif region in self.regions:
                previous_region = self.region
                self.region = region
                # clients are region-specific, so we need to recreate it
                self.client = self.create_client()
                try:
                    response = self.client.create_bucket(
                        ACL=acl if acl in BUCKET_ACL else 'private',
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                except Exception as err:
                    logger.exception(
                        f'Unable to create S3 bucket ({bucket_name}) using '
                        f'{self.access_key}: {str(err)}')
                    raise

                # reset the client to the original region
                logger.info(f'Resetting S3 client to previous settings '
                            f'in {previous_region}')
                self.region = previous_region
                self.create_client()
            else:
                logger.warning(f'Malformed region: {str(region)}')
        except self.client.exceptions.BucketAlreadyExists:
            logger.warning(f'S3 bucket ({bucket_name} already exists in '
                           f'{self.access_key}')
        except self.client.exceptions.BucketAlreadyOwnedByYou:
            logger.warning(f'S3 bucket is already Owned by {self.access_key}')
        except Exception as err:
            logger.exception(f'Unable to create S3 bucket ({bucket_name}'
                             f'using {self.access_key}: {str(err)}')
        finally:
            self.list_buckets()

    def bucket_exists(self, bucket_name) -> bool:
        """
        Query AWS to see if the given bucket exists.

        REQUIRES:
            s3:ListBucket
            s3:HeadBucket
            s3:ListAllMyBuckets

        :param bucket_name: The name of the bucket to search for as a string.
        :return: A boolean to show if the bucket exists or not.
        """
        bucket_name = self.prepare_name(bucket_name)
        try:
            self.list_buckets()
        except Exception:
            logger.exception(f'Unable to check if S3 bucket ({bucket_name}) '
                             f'exists in {self.access_key}')

        return bool(bucket_name in self.buckets)

    def list_objects(self, bucket_name: str, prefix: str = '') -> list:
        """
        Return all of the objects found in a given bucket_name. Optionally,
        a prefix (key) can be passed to limit results to the given prefix.
        This might be a LONG running query, especially if prefix is not
        passed. It also cannot be run async or threaded due to the wacky
        continuation token usage.

        REQUIRES:
            s3:ListBucket
            s3:HeadBucket
            s3:ListAllMyBuckets

        :param bucket_name: The name of the bucket to look in
        :param prefix: Any prefix/key that will limit results
        :return object_list: A list of all of the object names
        """
        bucket_name = self.prepare_name(bucket_name)
        prefix = self.prepare_name(prefix)

        object_list = list()

        try:  # pylint: disable=too-many-nested-blocks
            for objects in get_paginated_continuation_token_api(
                    functools.partial(self.client.list_objects_v2,
                                      Bucket=bucket_name,
                                      Prefix=prefix)
            ):
                if isinstance(objects, dict):
                    contents = objects.get('Contents')
                    if isinstance(contents, list):
                        for bucket_object in contents:
                            if isinstance(bucket_object, dict):
                                object_list.append(bucket_object.get('Key'))
                            else:
                                logger.warning(
                                    f'Malformed bucket object. Expected a dict, '
                                    f'got {type(bucket_object)}: '
                                    f'{str(bucket_object)} ')
                    else:
                        if contents is not None:
                            logger.warning(
                                f'Malformed bucket contents. Expected a '
                                f'list, got {type(contents)}: {str(contents)}')
                else:
                    logger.warning(f'Malformed S3 objects. Expected a dict, got '
                                   f'{type(objects)}: {str(objects)}')
        except self.client.exceptions.NoSuchBucket:
            logger.exception(f'S3 bucket ({bucket_name}) does not exist in '
                             f'{self.access_key}')
        except Exception:
            logger.exception(f'Unable to list objects in S3 bucket '
                             f'({bucket_name}) using {self.access_key}')

        return object_list

    def object_exists(self, bucket_name: str,
                      object_name: str,
                      prefix: str = ''
                      ) -> bool:
        """
        Determine if a given object exists in a given bucket/prefix. This
        returns a True/False.

        REQUIRES:
            s3:ListBucket
            s3:HeadBucket
            s3:ListAllMyBuckets

        :param bucket_name: The name of the bucket to look in to find
        the object as a string.
        :param object_name: The name of the object to search for as a string.
        :param prefix: The prefix (quasi-directory) to search in. This is
        HIGHLY recommended to use, whenever possible, since this function
        can be very long-running if the prefix is not supplied.
        :return return_code: A True/False that denotes if the object is
        found or not.
        """
        bucket_name = self.prepare_name(bucket_name)
        prefix = self.prepare_name(prefix)
        object_name = self.prepare_name(object_name)

        return_code = False
        for s3_object in self.list_objects(bucket_name=bucket_name,
                                           prefix=prefix):
            if isinstance(s3_object, str):
                if s3_object.endswith(object_name):
                    return_code = True
                    break
            else:
                logger.warning(f'Malformed S3 object name ({s3_object}). '
                               f'Expected a str, got {type(s3_object)}:'
                               f'{str(s3_object)}')
        return return_code

    def upload_object(self,
                      object_name: str,
                      bucket_name: str,
                      acl: str = '',
                      storage_class: str = '',
                      body: dict = None,
                      tags: str = None,
                      ) -> dict:
        """
        This function uploads data (either as a bytes object (in memory data)
        or a file object (existing on the localhost)) as *object_name into
        the desired S3 bucket (*bucket_name). Additional parameters are
        available to apply specific controls to the data on S3 in the form
        of canned ACL, storage type and support for custom tagging. We
        do check that the bucket exists before doing anything.

        REQUIRES:
            s3:PutObject
            s3:ListAllMyBuckets
            s3:PutBucketTagging
            s3:CreateBucket
            s3:ListBucket
            s3:PutObjectTagging
            s3:DeleteObject
            s3:HeadBucket
            s3:DeleteBucket

        :param object_name: A string representing the desired file name.
        :param bucket_name: A string defining the name of the target S3 bucket.
        :param acl: A string representing a canned access control list.
        :param storage_class: A string representing the desired storage class
        and should be one of the selections in OBJECT_STORAGE_CLASS.
        :param body: A dictionary/json of data to upload to S3 as *object_name.
        :param tags: URL-style tags to add to the uploaded object.
        :return response: A dictionary with information about the upload
        transaction. This data is currently not used, but is helpful when
        working with custom ACLs, storage classes and retention policies.
        """
        response = dict()
        if self.bucket_exists(bucket_name=bucket_name):
            bucket_name = self.prepare_name(bucket_name)
            object_name = self.prepare_name(object_name)

            default_tags = tags or f'Name={object_name}&UploadedBy=Axonius&Created={strftime("%Y-%m-%d %H:%M:%S")}'

            try:
                # upload in-memory data
                if body:
                    body = json.dumps(body).encode('utf-8')
                else:
                    body = open(object_name, 'rb')

                try:
                    response = self.client.put_object(
                        ACL=acl if acl in BUCKET_ACL else 'private',
                        Body=body,
                        Bucket=bucket_name,
                        StorageClass=storage_class if storage_class in OBJECT_STORAGE_CLASS else 'STANDARD',
                        Key=object_name,
                        Tagging=default_tags
                    )
                except Exception as err:
                    logger.exception(f'Unable to upload {object_name} to S3 '
                                     f'bucket ({bucket_name}) using '
                                     f'{self.access_key}: {str(err)}')
                finally:
                    if hasattr(body, 'close'):
                        body.close()
            except Exception as err:
                logger.exception(f'Unable to upload {object_name} to {bucket_name}: '
                                 f'{str(err)}')
        else:
            logger.warning(f'S3 bucket ({bucket_name}) does not exist')

        return response

    def download_object(self,
                        object_name: str,
                        bucket_name: str,
                        prefix: str = None
                        ):
        """
        After verifying that the bucket exists, upload a file-based object
        to the given bucket with the given prefix.

        REQUIRES:
            s3:GetObject
            s3:ListAllMyBuckets
            s3:ListBucket
            s3:HeadBucket

        :param object_name: The name of the local file and the destination
        S3 object as a string.
        :param bucket_name: The name of the target S3 bucket to place the
        file into.
        :param prefix: The prefix (quasi-directory) for the file object
        as a string.
        """
        if self.bucket_exists(bucket_name=bucket_name):
            bucket_name = self.prepare_name(bucket_name)
            object_name = self.prepare_name(object_name)

            if prefix:
                prefix = self.prepare_name(prefix)
                key_name = f'{prefix}/{object_name}'
            else:
                key_name = object_name

            try:
                with open(object_name, 'wb') as download_file:
                    try:
                        response = self.client.download_fileobj(
                            Bucket=bucket_name,
                            Key=key_name,
                            Fileobj=download_file
                        )
                    except Exception as err:
                        logger.exception(f'Unable to download {key_name} from '
                                         f'S3 bucket ({bucket_name}) using '
                                         f'{self.access_key}: {str(err)}')
            except Exception as err:
                logger.exception(f'Unable to open {object_name} from localhost: '
                                 f'{str(err)}')
        else:
            logger.warning(f'S3 bucket ({bucket_name}) does not exist')

    @staticmethod
    def prepare_name(name: str) -> str:
        """ Remove any trailing slashes before returning the name """
        name = name.replace('\\', '/')
        while name.endswith('/'):
            name = name[:-1]

        return name

    @staticmethod
    def get_available_regions() -> list:
        """ Query for all available regions (enabled in AWS IAM) """
        session = boto3.Session()
        regions = session.get_available_regions(service_name='s3')
        return regions if isinstance(regions, list) else []

    def prepare_json_file_name(self, key_name: str, data: dict) -> str:
        key_name = self.prepare_name(name=key_name)

        # append date
        append_datetime = data.get('append_datetime')
        if append_datetime:
            key_name = f'{key_name}-{datetime.datetime.now().strftime(STRFTIME_FORMAT)}'

        # handle json data
        return f'{key_name}.json'

    # pylint: disable=too-many-branches
    def send_data_to_s3(self, data: dict, data_type: str = 'json'):
        if not isinstance(data, dict):
            raise ValueError(f'Malformed data. Expected a dict, got {type(data)}: '
                             f'{str(data)}')

        if not isinstance(data_type, str):
            raise ValueError(f'Malformed data type. Cannot send to S3. Expected '
                             f'a str, got {type(data_type)}: {str(data_type)}')

        # prepare the bucket, we assume that the bucket exists
        bucket_name = data.get('bucket_name')
        if isinstance(bucket_name, str):
            bucket_name = self.prepare_name(name=bucket_name)
        else:
            logger.warning(f'Malformed S3 bucket name. Expected a string, '
                           f'got {type(bucket_name)}: {str(bucket_name)}')

        if not self.bucket_exists(bucket_name=bucket_name):
            raise ValueError(f'S3 bucket ({bucket_name}) does not exist')

        # prepare the key name
        key_name = data.get('key_name')
        if isinstance(key_name, str):
            key_name = self.prepare_json_file_name(key_name=key_name, data=data)
        else:
            logger.warning(f'Malformed S3 key name. Expected a string, got a '
                           f'{type(key_name)}: {str(key_name)}')

        # overwrite/preserve existing file
        overwrite_existing = data.get('overwrite_existing_file') if \
            isinstance(data.get('overwrite_existing_file'), bool) else False

        if not overwrite_existing:
            # Do not overwrite existing
            if self.object_exists(bucket_name=bucket_name,
                                  object_name=key_name):
                logger.warning(
                    f'File ({key_name}) already exists in {bucket_name} on '
                    f'account {self.access_key} and "Overwrite Existing '
                    f'File" is not enabled in settings')

        try:
            self.upload_object(
                object_name=key_name,
                bucket_name=bucket_name,
                body=data
            )
        except Exception as err:
            logger.exception(f'Unable to upload {key_name} to {bucket_name} '
                             f'using {self.access_key}: {str(err)}')
