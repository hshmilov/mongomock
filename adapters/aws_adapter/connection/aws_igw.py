import logging
from typing import Optional

from aws_adapter.connection.aws_route_table import populate_route_tables
from aws_adapter.connection.structures import AWSDeviceAdapter
from aws_adapter.connection.utils import get_paginated_next_token_api

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=inconsistent-return-statements
def query_devices_by_client_by_source_igw(client_data: dict) -> list:
    """
    Use the boto3, EC2 client from the passed *client_data to collect
    data on AWS Internet Gateways using pagination and yield them back to
    the caller.

    :param client_data: A boto3 client object used to connect to AWS' API
    """
    igw_client = client_data.get('ec2')
    if not igw_client:
        return

    try:
        for gateways_page in get_paginated_next_token_api(igw_client.describe_internet_gateways):
            if not isinstance(gateways_page, dict):
                raise ValueError(f'Malformed gateways page, expected dict, got '
                                 f'{type(gateways_page)}')

            if not isinstance(gateways_page.get('InternetGateways'), list):
                raise ValueError(f'Malformed IGW, expected a list, got '
                                 f'{type(gateways_page.get("InternetGateways"))}')

            for page in gateways_page.get('InternetGateways'):
                yield page
    except Exception:
        logger.exception(f'Failed to fetch AWS Internet Gateways.')


# pylint: disable=too-many-statements, too-many-nested-blocks, too-many-branches
def parse_raw_data_inner_igw(
        device: AWSDeviceAdapter,
        igw_data_raw: dict,
        generic_resources: dict,
        options: dict,
) -> Optional[AWSDeviceAdapter]:
    """
    Take the passed *igw_data_raw and add it to the AWSDeviceAdapter object
    before returning the object to the caller.

    :param device: The AWSDeviceAdapter object
    :param igw_data_raw: The raw data pulled from AWS that is used to
    populate the *device
    :param generic_resources: A dict containing generic information.
    :return device: A populated (optionally) AWSDeviceAdapter object
   """
    # Parse Internet Gateway data
    try:
        igw_id = igw_data_raw.get('InternetGatewayId')

        if igw_id and isinstance(igw_id, str):
            try:
                device.id = igw_id
                device.aws_device_type = 'InternetGateway'
                device.cloud_provider = 'AWS'

                device.igw_id = igw_id
                device.igw_owner_id = igw_data_raw.get('OwnerId')

                try:
                    attachments = igw_data_raw.get('Attachments')
                    if not isinstance(attachments, list):
                        raise ValueError(f'Malformed route attachments, '
                                         f'expected list, got '
                                         f'{type(attachments)}')

                    for attachment in attachments:
                        if not isinstance(attachment, dict):
                            raise ValueError(f'Malformed route attachment, '
                                             f'expected dict, got '
                                             f'{type(attachment)}')

                        state = attachment.get('State')
                        if isinstance(state, str):
                            device.igw_state = state.title()

                        if 'VpcId' in attachment:
                            device.vpc_id = attachment.get('VpcId')
                            device.igw_attached = True
                            continue

                except Exception:
                    logger.exception(f'Could not parse attachments: '
                                     f'{igw_data_raw}')

                try:
                    tags = igw_data_raw.get('Tags')
                    if not isinstance(tags, list):
                        raise ValueError(f'Malformed tags, expected a list, '
                                         f'got {type(tags)}: {str(tags)}')
                    name_tag = ''
                    device_tags = {tag['Key']: tag['Value'] for tag in tags} or {}

                    for key, value in device_tags.items():
                        if key == 'Name':
                            name_tag = value

                        device.add_aws_ec2_tag(key=key, value=value)
                        device.add_key_value_tag(key=key, value=value)

                    if name_tag:
                        device.name = name_tag
                    else:
                        device.name = igw_id

                except Exception:
                    logger.exception(f'Could not parse tags: {igw_data_raw}')

                # route tables
                if options.get('fetch_route_table_for_devices'):
                    route_tables = generic_resources.get('route_tables') or []
                    try:
                        if not isinstance(route_tables, list):
                            raise ValueError(
                                f'Malformed route tables, expected list, '
                                f'got {type(route_tables)}')

                        populate_route_tables(device, route_tables)
                    except Exception:
                        logger.exception(f'Unable to populate route tables'
                                         f'{str(route_tables)} for '
                                         f'{str(device.id)}')

                device.set_raw(igw_data_raw)
                return device
            except Exception:
                logger.exception(f'Problem parsing Internet Gateway: '
                                 f'{igw_data_raw}')

    except Exception:
        logger.exception(f'No ID found for Internet Gateway {igw_data_raw}')
