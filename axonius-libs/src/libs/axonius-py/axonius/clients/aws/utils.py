import logging

from typing import Optional

import boto3
logger = logging.getLogger(f'axonius.{__name__}')


def get_s3_object(
        bucket_name: str,
        object_location: str,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None
):
    """
    Gets an object from an s3 bucket.
    :param bucket_name: the name of the bucket.
    :param object_location: the location of the object within the bucket.
    :param access_key_id: access key id to access the bucket. pass None to use the instance attached IAM role.
    :param secret_access_key: secret access key to access the bucket. pass None to use the instance attached IAM role.
    :return:
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
    )
    s3_object = s3_client.get_object(Bucket=bucket_name, Key=object_location)
    if 'Body' not in s3_object:
        raise ValueError(f'Bad response: {s3_object}')
    return s3_object['Body'].read()


def download_s3_object_to_file_obj(
        bucket_name: str,
        key: str,
        file_obj,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None
):
    """
    Gets an object from an s3 bucket.
    :param bucket_name: the name of the bucket.
    :param key: the location of the object within the bucket.
    :param access_key_id: access key id to access the bucket. pass None to use the instance attached IAM role.
    :param secret_access_key: secret access key to access the bucket. pass None to use the instance attached IAM role.
    :return:
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
    )
    s3_client.download_fileobj(bucket_name, key, file_obj)


def aws_list_s3_objects(
        bucket_name: str,
        prefix: str = '',
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        just_one: bool = False
):
    """
    Lists objects within an s3 bucket and key
    :param bucket_name: the name of the bucket.
    :param prefix: prefix
    :param access_key_id: access key id to access the bucket. pass None to use the instance attached IAM role.
    :param secret_access_key: secret access key to access the bucket. pass None to use the instance attached IAM role.
    :param just_one: Fetch just one (useful for testing permissions)
    :return:
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
    )

    if just_one:
        yield from (s3_client.list_objects(Bucket=bucket_name, Prefix=prefix, MaxKeys=1).get('Contents') or [])
    else:
        for object_page in s3_client.get_paginator('list_objects').paginate(
                Bucket=bucket_name,
                Prefix=prefix
        ):
            yield from (object_page.get('Contents') or [])


def upload_file_to_s3(
        bucket_name: str,
        key_name: str,
        file_obj,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None
):
    """
    Uploads a file to s3.
    This is a managed transfer which will perform a multipart upload in multiple threads if necessary.
    :param bucket_name: the name of the bucket.
    :param key_name: the location of the object within the bucket.
    :param file_obj: a file-like object
    :param access_key_id: optional access key id to access the bucket. pass None to use the instance attached IAM role.
    :param secret_access_key: optional secret access key to access the bucket.
                              pass None to use the instance attached IAM role.
    :return:
    :return:
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
    )
    s3_client.upload_fileobj(file_obj, bucket_name, key_name, ExtraArgs={'ACL': 'bucket-owner-full-control'})


def delete_file_from_s3(
        bucket_name: str,
        key_name: str,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None
):
    """
    Deletes the specific key from an s3 object.
    :param bucket_name: the name of the bucket.
    :param key_name: the object key
    :param access_key_id: access key id to access the bucket. pass None to use the instance attached IAM role.
    :param secret_access_key: secret access key to access the bucket. pass None to use the instance attached IAM role.
    :return:
    :return:
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
    )

    s3_client.delete_object(
        Bucket=bucket_name,
        Key=key_name
    )


def does_s3_key_exist(
        bucket_name: str,
        key_name: str,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None
):
    """
    Checks if s3 file exists
    :param bucket_name: the name of the bucket.
    :param key_name: the object key
    :param access_key_id: access key id to access the bucket. pass None to use the instance attached IAM role.
    :param secret_access_key: secret access key to access the bucket. pass None to use the instance attached IAM role.
    :return:
    :return:
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
    )

    try:
        s3_client.head_object(
            Bucket=bucket_name,
            Key=key_name
        )
        return True
    except Exception as e:
        if '404' in str(e):
            return False
        raise
