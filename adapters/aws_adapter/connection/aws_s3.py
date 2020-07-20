import json
import logging
from typing import Optional

from botocore.exceptions import ClientError

from aws_adapter.connection.aws_cloudfront import fetch_cloudfront
from aws_adapter.connection.structures import AWSDeviceAdapter, AWSS3BucketACL, AWSS3BucketPolicy, \
    AWSS3PublicAccessBlockConfiguration
from aws_adapter.connection.utils import parse_bucket_policy_statements

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements
def query_devices_by_client_by_source_s3(client_data: dict, cloudfront_data: dict):
    if client_data.get('s3') is not None:
        try:
            cloudtrail_s3_bucket_names = None
            if client_data.get('cloudtrail') is not None:
                try:
                    cloudtrail_s3_bucket_names = set()
                    for trail in (client_data.get('cloudtrail').describe_trails().get('trailList') or []):
                        if trail.get('S3BucketName'):
                            cloudtrail_s3_bucket_names.add(trail['S3BucketName'])
                    cloudtrail_s3_bucket_names = list(cloudtrail_s3_bucket_names)
                except Exception:
                    logger.exception(f'Failed getting cloudtrail s3 bucket names')

            s3_client = client_data.get('s3')
            # No pagination for this api..
            list_buckets_response = s3_client.list_buckets()
            owner_display_name = (list_buckets_response.get('Owner') or {}).get('DisplayName')
            owner_id = (list_buckets_response.get('Owner') or {}).get('ID')
            for bucket_raw in (list_buckets_response.get('Buckets') or []):
                bucket_raw['owner_display_name'] = owner_display_name
                bucket_raw['owner_id'] = owner_id
                bucket_name = bucket_raw.get('Name')

                try:
                    bucket_acl = s3_client.get_bucket_acl(Bucket=bucket_name)
                    if bucket_acl.get('Grants'):
                        bucket_raw['acls'] = bucket_acl.get('Grants')
                except Exception:
                    pass

                try:
                    bucket_policy_status = s3_client.get_bucket_policy_status(Bucket=bucket_name)
                    bucket_raw['is_public'] = (bucket_policy_status.get('PolicyStatus') or {}).get('IsPublic')
                except Exception:
                    pass

                try:
                    bucket_policy = s3_client.get_bucket_policy(Bucket=bucket_name)
                    bucket_raw['policy'] = (bucket_policy.get('Policy') or {})
                except Exception:
                    pass

                try:
                    bucket_location_status = s3_client.get_bucket_location(Bucket=bucket_name)
                    bucket_raw['location'] = bucket_location_status.get('LocationConstraint')
                except Exception:
                    pass

                try:
                    bucket_location_status = s3_client.get_public_access_block(Bucket=bucket_name)
                    bucket_raw['access_block'] = bucket_location_status.get('PublicAccessBlockConfiguration')
                except Exception:
                    pass

                try:
                    bucket_logging_target = s3_client.get_bucket_logging(Bucket=bucket_name)
                    logging_enabled = bucket_logging_target.get('LoggingEnabled') or {}
                    if logging_enabled.get('TargetBucket'):
                        bucket_raw['logging_target_bucket'] = logging_enabled.get('TargetBucket')
                except Exception:
                    pass

                try:
                    if cloudtrail_s3_bucket_names:
                        bucket_raw['s3_bucket_used_for_cloudtrail'] = bucket_name in cloudtrail_s3_bucket_names
                except Exception:
                    pass

                # s3 tag query
                try:
                    s3_tag_response = s3_client.get_bucket_tagging(
                        Bucket=bucket_name)
                    if isinstance(s3_tag_response, dict):
                        s3_tags = s3_tag_response.get('TagSet')
                        if isinstance(s3_tags, list):
                            bucket_raw['tags'] = s3_tags
                        else:
                            logger.warning(
                                f'Malformed s3 tags. Expected a list, got '
                                f'{type(s3_tags)}: {str(s3_tags)}')
                    else:
                        logger.warning(
                            f'Malformed S3 bucket tag response. Expected a '
                            f'dict, got {type(s3_tag_response)}: '
                            f'{str(s3_tag_response)}')
                except ClientError:
                    # a ClientError.NoSuchTagSet error is thrown if none found
                    # no need to handle it, just move along
                    pass
                except Exception as err:
                    logger.warning(f'Unable to fetch s3 bucket tags for '
                                   f'{bucket_name}: {err}')

                try:
                    if cloudfront_data:
                        bucket_raw['cloudfront'] = cloudfront_data
                except Exception:
                    pass

                yield bucket_raw

        except Exception:
            logger.exception(f'Problem fetching information about S3')


def parse_raw_data_inner_s3(
        device: AWSDeviceAdapter,
        s3_bucket_raw: dict,
        generic_resources: dict,
        options: dict
) -> Optional[AWSDeviceAdapter]:
    # Parse S3 Buckets
    try:
        s3_bucket_name = s3_bucket_raw.get('Name')
        device.id = s3_bucket_name
        device.name = s3_bucket_raw.get('Name')
        device.aws_device_type = 'S3'
        device.cloud_provider = 'AWS'

        device.s3_bucket_name = s3_bucket_name
        device.s3_bucket_url = f'https://{str(s3_bucket_name)}.s3.amazonaws.com'
        device.s3_creation_date = s3_bucket_raw.get('CreationDate')
        device.s3_owner_name = s3_bucket_raw.get('owner_display_name')
        device.s3_owner_id = s3_bucket_raw.get('owner_id')

        has_public_acl = False
        for acl_raw in (s3_bucket_raw.get('acls') or []):
            acl_raw_grantee = acl_raw.get('Grantee') or {}
            device.s3_bucket_acls.append(
                AWSS3BucketACL(
                    grantee_display_name=acl_raw_grantee.get('DisplayName'),
                    grantee_email_address=acl_raw_grantee.get('EmailAddress'),
                    grantee_id=acl_raw_grantee.get('ID'),
                    grantee_type=acl_raw_grantee.get('Type'),
                    grantee_uri=acl_raw_grantee.get('URI'),
                    grantee_permission=acl_raw.get('Permission'),
                )
            )
            if acl_raw_grantee.get('URI') and 'groups/global/AllUsers' in acl_raw_grantee.get('URI'):
                has_public_acl = True
            if acl_raw_grantee.get('URI') and 'groups/global/AuthenticatedUsers' in acl_raw_grantee.get('URI'):
                has_public_acl = True

        if has_public_acl:
            device.s3_bucket_is_public = True
        else:
            device.s3_bucket_is_public = s3_bucket_raw.get('is_public')

        device.s3_bucket_location = s3_bucket_raw.get('location')

        try:
            bucket_policy = s3_bucket_raw.get('policy')
            bucket_policy_parsed = {}
            try:
                bucket_policy_parsed = json.loads(bucket_policy)
            except Exception:
                pass
            s3_bucket_raw['policy_parsed'] = bucket_policy_parsed
            statements = parse_bucket_policy_statements(bucket_policy_parsed)

            if bucket_policy:
                device.s3_bucket_policy = AWSS3BucketPolicy(
                    bucket_policy_id=bucket_policy_parsed.get('Id'),
                    bucket_policy=bucket_policy,
                    statements=statements
                )
        except Exception:
            logger.exception(f'Problem parsing bucket policy')

        try:
            public_access_block = s3_bucket_raw.get('access_block')
            if isinstance(public_access_block, dict) and public_access_block:
                device.s3_public_access_block_policy = AWSS3PublicAccessBlockConfiguration(
                    block_public_acls=public_access_block.get('BlockPublicAcls'),
                    ignore_public_acls=public_access_block.get('IgnorePublicAcls'),
                    block_public_policy=public_access_block.get('BlockPublicPolicy'),
                    restrict_public_buckets=public_access_block.get('RestrictPublicBuckets')
                )
        except Exception:
            logger.exception(f'Problem parsing public access block')

        try:
            if s3_bucket_raw.get('logging_target_bucket'):
                device.s3_bucket_logging_target = s3_bucket_raw.get('logging_target_bucket')
        except Exception:
            logger.exception(f'Problem setting bucket logging target')

        try:
            if s3_bucket_raw.get('s3_bucket_used_for_cloudtrail'):
                device.s3_bucket_used_for_cloudtrail = s3_bucket_raw.get('s3_bucket_used_for_cloudtrail')
        except Exception:
            logger.exception(f'Problem setting s3 cloudtrail status')

        try:
            tags = s3_bucket_raw.get('tags')
            if tags and isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, dict):
                        device.add_aws_s3_tag(key=tag.get('Key'),
                                              value=tag.get('Value')
                                              )
                    else:
                        logger.warning(f'Malformed s3 tag. Expected a dict, '
                                       f'got {type(tag)}: {str(tag)}')
            else:
                if tags is not None:
                    logger.warning(f'Malformed s3 tags. Expected a list, got '
                                   f'{type(tags)}: {str(tags)}')
        except Exception:
            logger.exception(f'Unable to parse s3 tags: '
                             f'{str(s3_bucket_raw.get("tags"))}')

        # cloudfront
        try:
            cloudfront_distributions = s3_bucket_raw.get('cloudfront')
            if cloudfront_distributions and \
                    isinstance(cloudfront_distributions, dict):
                fetch_cloudfront(device=device,
                                 distributions=cloudfront_distributions)
            else:
                if cloudfront_distributions is not None:
                    logger.warning(f'Malformed Cloudfront distributions. Expected '
                                   f'a dict, got {type(cloudfront_distributions)}: '
                                   f'{str(cloudfront_distributions)}')
        except Exception:
            logger.exception(f'Unable to populate Cloudfront distributions '
                             f'for {device.aws_device_type} resource: '
                             f'{device.name}')

        device.set_raw(s3_bucket_raw)
        return device
    except Exception:
        logger.exception(f'Problem parsing s3 bucket')
