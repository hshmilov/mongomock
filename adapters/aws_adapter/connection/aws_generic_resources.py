# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements, too-many-locals
import logging

from aws_adapter.connection.utils import get_paginated_marker_api, get_paginated_next_token_api

logger = logging.getLogger(f'axonius.{__name__}')


def query_aws_generic_region_resources(client_data: dict) -> dict:
    ec2_client_data = client_data.get('ec2')
    if not ec2_client_data:
        return {}

    described_vpcs = dict()
    try:
        for describe_vpcs_page in ec2_client_data.get_paginator('describe_vpcs').paginate():
            for vpc_raw in describe_vpcs_page.get('Vpcs') or []:
                vpc_id = vpc_raw.get('VpcId')
                if not vpc_id:
                    continue
                vpc_tags = dict()

                for vpc_tag_raw in (vpc_raw.get('Tags') or []):
                    try:
                        vpc_tags[vpc_tag_raw['Key']] = vpc_tag_raw['Value']
                    except Exception:
                        logger.exception(f'Error while parsing vpc tag {vpc_tag_raw}')

                described_vpcs[vpc_id] = vpc_tags
    except Exception:
        logger.exception('Could not describe aws vpcs')

    security_groups_dict = dict()
    try:
        for security_group_raw_answer in get_paginated_next_token_api(
                ec2_client_data.describe_security_groups):
            for security_group in security_group_raw_answer['SecurityGroups']:
                if security_group.get('GroupId'):
                    security_groups_dict[security_group.get('GroupId')] = security_group

    except Exception:
        logger.exception(f'Problem getting security_groups')

    subnets_dict = dict()
    try:
        for subnets_page in ec2_client_data.get_paginator('describe_subnets').paginate():
            for subnet_raw in (subnets_page.get('Subnets') or []):
                subnet_id = subnet_raw['SubnetId']
                subnet_tags = dict()
                for subnet_tag_raw in (subnet_raw.get('Tags') or []):
                    try:
                        subnet_tags[subnet_tag_raw['Key']] = subnet_tag_raw['Value']
                    except Exception:
                        logger.exception(f'problem parsing {subnet_tag_raw}')

                subnets_dict[subnet_id] = {
                    'name': subnet_tags.get('Name'),
                    'vpc_id': subnet_raw.get('VpcId')
                }
    except Exception:
        logger.exception(f'could not parse subnets')

    return {
        'vpcs': described_vpcs,
        'security_groups': security_groups_dict,
        'subnets': subnets_dict
    }


def get_account_metadata(client_data):
    iam_client = client_data.get('iam')
    sts_client = client_data.get('sts')
    account_metadata = dict()
    if iam_client:
        try:
            all_aliases = []
            for list_account_aliases_page in get_paginated_marker_api(iam_client.list_account_aliases):
                all_aliases.extend(list_account_aliases_page.get('AccountAliases') or [])

            account_metadata['aliases'] = all_aliases
        except Exception:
            logger.exception(f'Exception while querying account aliases')

    if sts_client:
        try:
            account_metadata['account_id'] = sts_client.get_caller_identity()['Account']
        except Exception:
            logger.exception(f'Exception while querying account id')

    for generic_key in ['account_tag']:
        if generic_key in client_data:
            account_metadata[generic_key] = client_data[generic_key]

    return account_metadata
