# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements, too-many-locals
import logging
from typing import Optional

from aws_adapter.connection.aws_route_table import populate_route_tables
from aws_adapter.connection.structures import AWSDeviceAdapter
from aws_adapter.connection.utils import get_paginated_next_token_api

logger = logging.getLogger(f'axonius.{__name__}')


def query_devices_by_client_by_source_nat(client_data: dict):
    ec2_client_data = client_data.get('ec2')
    if not ec2_client_data:
        return

    try:
        for nat_gateways_page in get_paginated_next_token_api(ec2_client_data.describe_nat_gateways):
            yield from (nat_gateways_page.get('NatGateways') or [])
    except Exception:
        logger.exception('Problem getting NAT Gateways')


def parse_raw_data_inner_nat(
        device: AWSDeviceAdapter,
        nat_gateway_raw: dict,
        generic_resources: dict,
        options: dict
) -> Optional[AWSDeviceAdapter]:
    # Parse NAT
    subnets_by_id = generic_resources.get('subnets') or {}
    vpcs_by_id = generic_resources.get('vpcs') or {}
    route_tables = generic_resources.get('route_tables') or []

    try:
        device.id = nat_gateway_raw['NatGatewayId']

        device.aws_device_type = 'NAT'

        tags_dict = {i['Key']: i['Value'] for i in nat_gateway_raw.get('Tags', {})}
        for key, value in tags_dict.items():
            device.add_aws_ec2_tag(key=key, value=value)
            device.add_key_value_tag(key, value)

        vpc_id = nat_gateway_raw.get('VpcId')
        if vpc_id and isinstance(vpc_id, str):
            vpc_id = vpc_id.lower()
            device.vpc_id = vpc_id
            device.vpc_name = (vpcs_by_id.get(vpc_id) or {}).get('Name')
            try:
                for vpc_tag_key, vpc_tag_value in (vpcs_by_id.get(vpc_id) or {}).items():
                    device.add_aws_vpc_tag(key=vpc_tag_key, value=vpc_tag_value)
            except Exception:
                logger.exception(f'Could not parse aws vpc tags')

        subnet_id = nat_gateway_raw.get('SubnetId')
        if subnet_id:
            device.subnet_id = subnet_id
            device.subnet_name = (subnets_by_id.get(subnet_id) or {}).get('name')
        device.name = tags_dict.get('Name')

        for nat_gateway_nic in (nat_gateway_raw.get('NatGatewayAddresses') or []):
            private_ip = nat_gateway_nic.get('PrivateIp')
            public_ip = nat_gateway_nic.get('PublicIp')
            ips = []
            if private_ip:
                ips.append(private_ip)
            if public_ip:
                ips.append(public_ip)
                device.add_public_ip(public_ip)
            device.add_nic(ips=ips)

        # route tables
        if options.get('fetch_route_table_for_devices'):
            try:
                if not isinstance(route_tables, list):
                    raise ValueError(f'Malformed route tables, expected list, '
                                     f'got {type(route_tables)}')

                populate_route_tables(device, route_tables)
            except Exception:
                logger.exception(f'Unable to populate route tables: '
                                 f'{str(route_tables)} for '
                                 f'{str(device.id)}')

        device.set_raw(nat_gateway_raw)
        return device
    except Exception:
        logger.exception(f'Problem parsing NAT gateway')
