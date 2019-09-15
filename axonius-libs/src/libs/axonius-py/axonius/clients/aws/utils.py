from typing import Optional

import boto3


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
