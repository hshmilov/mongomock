import logging
from typing import Optional

from axonius.utils.datetime import parse_date
from axonius.utils.parsing import parse_bool_from_raw

from aws_adapter.connection.structures import AWSDeviceAdapter, \
    AWSCidrBlockAssociationSet, AWSVPCPeeringConnection, AWSVPCPeeringVPCInfo, \
    AWSVPCPeeringOptions, AWSTagKeyValue
from aws_adapter.consts import INSTANCE_TENANCY, CIDR_BLOCK_STATE, VPC_STATE, \
    VPC_PEERING_STATUS_CODE
from aws_adapter.connection.utils import get_paginated_next_token_api

logger = logging.getLogger(f'axonius.{__name__}')


def query_peering_connections(vpc_client) -> list:
    peering_connections = list()
    try:
        for peering_page in get_paginated_next_token_api(
                vpc_client.describe_vpc_peering_connections):
            if not (peering_page and isinstance(peering_page, dict)):
                logger.warning(
                    f'Malformed data in describe vpc peering connections, '
                    f'expected a dict, got {type(peering_page)}: {str(peering_page)}')
                continue

            for page in peering_page.get('VpcPeeringConnections') or []:
                if not (page and isinstance(page, dict)):
                    if page:
                        logger.warning(
                            f'Malformed data in VPC peering page. Expected a dict, '
                            f'got {type(page)}: {str(page)}')
                    continue
                peering_connections.append(page)

        return peering_connections
    except Exception:
        logger.exception(f'Failed to fetch VPC peering information')


# pylint: disable=too-many-branches
def query_devices_by_client_by_source_vpc(client_data: dict) -> list:
    vpc_raw_data = dict()

    vpc_client = client_data.get('ec2')
    if not vpc_client:
        return

    try:
        peering_connections = query_peering_connections(vpc_client)
        if not (peering_connections and isinstance(peering_connections, list)):
            if peering_connections:
                logger.warning(
                    f'Malformed VPC peering connections. Expected a list, '
                    f'got {type(peering_connections)}: {str(peering_connections)}')
        else:
            vpc_raw_data['peering_data'] = peering_connections
    except Exception as err:
        logger.exception(f'Unable to query VPC peering connections: {str(err)}')

    try:
        for vpc_page in get_paginated_next_token_api(
                vpc_client.describe_vpcs):
            if not (vpc_page and isinstance(vpc_page, dict)):
                logger.warning(f'Malformed data in describe vpcs, expected a '
                               f'dict, got {type(vpc_page)}: {str(vpc_page)}')
                continue

            for page in vpc_page.get('Vpcs') or []:
                if not (page and isinstance(page, (dict, list))):
                    if page:
                        logger.warning(
                            f'Malformed data in VPC page, expected a dict or a '
                            f'list, got {type(page)}: {str(page)}')
                    continue

                # this data can be either a list or a dict, so handle appropriately\
                if isinstance(page, list):
                    for list_page in page:
                        vpc_raw_data['vpc_data'] = list_page
                        yield vpc_raw_data
                else:
                    vpc_raw_data['vpc_data'] = page
                    yield vpc_raw_data
    except Exception:
        logger.exception(f'Failed to fetch AWS VPCs.')


def parse_cidr_block_set(cidr_block_set: list, version: int = 4) -> Optional[list]:
    if version == 6:
        cidr = [cidr_block.get('Ipv6CidrBlock') for cidr_block in cidr_block_set]
    elif version == 4:
        cidr = [cidr_block.get('CidrBlock') for cidr_block in cidr_block_set]
    else:
        cidr = None

    return cidr


def parse_peering_endpoint(raw_data: dict) -> AWSVPCPeeringVPCInfo:
    peering_options = raw_data.get('PeeringOptions')
    if not (peering_options and isinstance(peering_options, dict)):
        if peering_options:
            logger.warning(f'Malformed peering options. Expected a dict, got '
                           f'{type(peering_options)}: {str(peering_options)}')
        peering_options_object = None
    else:
        peering_options_object = AWSVPCPeeringOptions(
            allow_dns_resolution_from_remote_vpc=parse_bool_from_raw(
                peering_options.get('AllowDnsResolutionFromRemoteVpc')),
            allow_egress_from_local_classiclink_to_remote_vpc=parse_bool_from_raw(
                peering_options.get('AllowEgressFromLocalClassicLinkToRemoteVpc')),
            allow_egress_from_local_vpc_to_remote_classiclink=parse_bool_from_raw(
                peering_options.get('AllowEgressFromLocalVpcToRemoteClassicLink'))
        )

    ipv6_cidr_block_set = raw_data.get('Ipv6CidrBlockSet')
    if not (ipv6_cidr_block_set and isinstance(ipv6_cidr_block_set, list)):
        if ipv6_cidr_block_set:
            logger.warning(f'Malformed IPv6 CIDR block set. Expected a list, '
                           f'got {type(ipv6_cidr_block_set)}: {str(ipv6_cidr_block_set)}')
        ipv6_cidr = None
    else:
        ipv6_cidr = parse_cidr_block_set(cidr_block_set=ipv6_cidr_block_set,
                                         version=6
                                         )

    ipv4_cidr_block_set = raw_data.get('CidrBlockSet')
    if not (ipv4_cidr_block_set and isinstance(ipv4_cidr_block_set, list)):
        if ipv4_cidr_block_set:
            logger.warning(f'Malformed IPv4 CIDR block set. Expected a list, '
                           f'got {type(ipv4_cidr_block_set)}: {str(ipv4_cidr_block_set)}')
        ipv4_cidr = None
    else:
        ipv4_cidr = parse_cidr_block_set(cidr_block_set=ipv4_cidr_block_set,
                                         version=4
                                         )

    peer = AWSVPCPeeringVPCInfo(
        cidr_block=raw_data.get('CidrBlock'),
        ipv6_cidr_block_set=ipv6_cidr,
        ipv4_cidr_block_set=ipv4_cidr,
        owner_id=raw_data.get('OwnerId'),
        peering_options=peering_options_object,
        vpc_id=raw_data.get('VpcId'),
        region=raw_data.get('Region')
    )

    return peer


def parse_peering_connections(raw_data: dict) -> AWSVPCPeeringConnection:
    accepter_info = raw_data.get('AccepterVpcInfo')
    if not (accepter_info and isinstance(accepter_info, dict)):
        if accepter_info:
            logger.warning(f'Malformed accepter information. Expected a dict, got '
                           f'{type(accepter_info)}: {str(accepter_info)}')
    try:
        accepter = parse_peering_endpoint(raw_data=accepter_info)
    except Exception as err:
        logger.exception(f'Unable to parse accepter peering endpoint: {str(err)}')
        accepter = None

    requester_info = raw_data.get('RequesterVpcInfo')
    if not (requester_info and isinstance(requester_info, dict)):
        if requester_info:
            logger.warning(f'Malformed accepter information. Expected a dict, got '
                           f'{type(requester_info)}: {str(requester_info)}')
    try:
        requester = parse_peering_endpoint(raw_data=requester_info)
    except Exception as err:
        logger.exception(f'Unable to parse requester peering endpoint: {str(err)}')
        requester = None

    status = raw_data.get('Status')
    if not (status and isinstance(status, dict)):
        if status:
            logger.warning(f'Malformed peering connection status. Expected a dict, '
                           f'got {type(status)}: {str(status)}')
        status_code = None
        status_message = None
    else:
        status_code = status.get('Code')
        if status_code and status_code not in VPC_PEERING_STATUS_CODE:
            logger.error(f'New field found in peering status code: '
                         f'{str(status_code)} not in {VPC_PEERING_STATUS_CODE}')
            status_code = None

        status_message = status.get('Message')

    try:
        tags_raw = raw_data.get('Tags')
        if isinstance(tags_raw, list):
            tags = list({AWSTagKeyValue(key=tag.get('Key'), value=tag.get('Value')) for tag in tags_raw})
    except Exception as err:
        logger.exception(f'Unable to parse tags: {str(err)}')
        tags = None

    peering_connection = AWSVPCPeeringConnection(
        connection_id=raw_data.get('VpcPeeringConnectionId'),
        accepter_vpc_info=accepter,
        requester_vpc_info=requester,
        expiration_time=parse_date(raw_data.get('ExpirationTime')),
        status_code=status_code,
        status_message=status_message,
        tags=tags
    )

    return peering_connection


def parse_tags(tags: list, vpc_id: str, device: AWSDeviceAdapter):
    name_tag = ''
    device_tags = {tag.get('Key'): tag.get('Value') for tag in tags} or {}

    for key, value in device_tags.items():
        if key == 'Name':
            name_tag = value

        device.add_aws_vpc_tag(key=key, value=value)
        device.add_key_value_tag(key=key, value=value)

    if name_tag:
        device.name = name_tag
    else:
        device.name = vpc_id


def parse_peering_data(peering_raw_data: list, vpc_id: str, device: AWSDeviceAdapter):
    for peer in peering_raw_data:
        if not (peer and isinstance(peer, dict)):
            if peer:
                logger.warning(f'Malformed peering data. Expected a '
                               f'dict, got {type(peer)}: {str(peer)}')
            continue

        accepter = peer.get('AccepterVpcInfo')
        if not (accepter and isinstance(accepter, dict)):
            if accepter:
                logger.warning(f'Malformed accepter. Expected a dict, got '
                               f'{type(accepter)}: {str(accepter)}')
            accepter_vpc_id = None
        else:
            accepter_vpc_id = accepter.get('VpcId')

        requester = peer.get('RequesterVpcInfo')
        if not (requester and isinstance(requester, dict)):
            if requester:
                logger.warning(f'Malformed requester. Expected a dict, got '
                               f'{type(requester)}: {str(requester)}')
            requester_vpc_id = None
        else:
            requester_vpc_id = requester.get('VpcId')

        if vpc_id in [accepter_vpc_id, requester_vpc_id]:
            try:
                peering_connections = parse_peering_connections(raw_data=peer)
                device.peering_connections.append(peering_connections)
            except Exception as err:
                logger.exception(
                    f'Unable to parse peering connections: {str(err)}')


# pylint: disable=too-many-locals, too-many-nested-blocks, inconsistent-return-statements, too-many-branches, too-many-statements
def parse_raw_data_inner_vpc(device: AWSDeviceAdapter,
                             devices_raw_data: dict) -> Optional[AWSDeviceAdapter]:
    peering_raw_data = devices_raw_data.get('peering_data')
    vpc_raw_data = devices_raw_data.get('vpc_data')

    if not (vpc_raw_data and isinstance(vpc_raw_data, dict)):
        if vpc_raw_data:
            logger.warning(f'Malformed vpc_raw_data. Expected a dict, got '
                           f'{type(vpc_raw_data)}: {str(vpc_raw_data)}')
        return None

    try:
        vpc_id = vpc_raw_data.get('VpcId')
        if not (vpc_id and isinstance(vpc_id, str)):

            if vpc_id:
                raise ValueError(f'Malformed VPC ID in raw data. Expected a '
                                 f'str, got {type(vpc_id)}: {str(vpc_id)}')

        owner_id = vpc_raw_data.get('OwnerId')
        if not (owner_id and isinstance(owner_id, str)):
            if owner_id:
                logger.error(f'Malformed Owner ID in raw data. Expected a '
                             f'str, got {type(owner_id)}: {str(owner_id)}')

        state = vpc_raw_data.get('State')
        if state and state not in VPC_STATE:
            logger.error(f'New field found in state: '
                         f'{str(state)} not in {state}')
            state = ''

        instance_tenancy = vpc_raw_data.get('InstanceTenancy')
        if instance_tenancy and instance_tenancy not in INSTANCE_TENANCY:
            logger.error(f'New field found in instance tenancy: '
                         f'{str(instance_tenancy)} not in {INSTANCE_TENANCY}')
            instance_tenancy = ''

        try:
            # generic fields
            device.id = f'{vpc_id}_{owner_id}'
            device.cloud_id = vpc_id
            device.aws_device_type = 'VPC'
            device.cloud_provider = 'AWS'
            # vpc-specific fields
            device.cidr_block = vpc_raw_data.get('CidrBlock')
            device.dhcp_options_id = vpc_raw_data.get('DhcpOptionsId')
            device.state = state
            device.vpc_id = vpc_id
            device.vpc_owner_id = vpc_raw_data.get('OwnerId')
            device.instance_tenancy = instance_tenancy
            device.is_default = parse_bool_from_raw(vpc_raw_data.get('IsDefault'))

            if not (peering_raw_data and isinstance(peering_raw_data, list)):
                if peering_raw_data:
                    logger.warning(f'Malformed raw peering data. Expected a '
                                   f'list, got {type(peering_raw_data)}: '
                                   f'{str(peering_raw_data)}')
            else:
                try:
                    parse_peering_data(peering_raw_data, vpc_id, device)
                except Exception as err:
                    logger.exception(f'Unable to parse peering data: {str(err)}')

            try:
                tags = vpc_raw_data.get('Tags')
                if not (tags and isinstance(tags, list)):
                    if tags:
                        logger.warning(f'Malformed tags, expected a list, '
                                       f'got {type(tags)}: {str(tags)}')
                else:
                    parse_tags(tags=tags, vpc_id=vpc_id, device=device)
            except Exception:
                logger.exception(f'Could not parse tags: {vpc_raw_data}')
        except Exception:
            logger.exception(f'Could not parse VPC data: {str(vpc_raw_data)}')

        # ipv4 cidr block association sets
        try:
            cidr_block_assoc_set = vpc_raw_data.get('CidrBlockAssociationSet')
            if cidr_block_assoc_set and isinstance(cidr_block_assoc_set, list):
                parse_association_set(device=device,
                                      cidr_block_assoc_set=cidr_block_assoc_set,
                                      version=4)
        except Exception:
            logger.exception(f'Unable to parse IPv4 CIDR block association '
                             f'sets: {str(vpc_raw_data)}')

        # ipv6 cidr block association sets
        try:
            cidr_block_assoc_set = vpc_raw_data.get('Ipv6CidrBlockAssociationSet')
            if cidr_block_assoc_set and isinstance(cidr_block_assoc_set, list):
                parse_association_set(device=device,
                                      cidr_block_assoc_set=cidr_block_assoc_set,
                                      version=6)
        except Exception:
            logger.exception(f'Unable to parse IPv6 CIDR block association '
                             f'sets: {str(vpc_raw_data)}')
        device.set_raw(devices_raw_data)

        return device

    except Exception as err:
        logger.exception(f'Unable to parse VPC data due to error: {str(err)}')


def parse_association_set(device: AWSDeviceAdapter,
                          cidr_block_assoc_set: list,
                          version: int = 4,
                          ):
    association_sets = list()
    if not (cidr_block_assoc_set and isinstance(cidr_block_assoc_set, list)):
        if cidr_block_assoc_set:
            logger.warning(
                f'Malformed CIDR block association set. Expected a '
                f'list, got {type(cidr_block_assoc_set)}: '
                f'{str(cidr_block_assoc_set)}')
    else:
        for association_set in cidr_block_assoc_set:
            if not (association_set and isinstance(association_set, dict)):
                if association_set:
                    logger.warning(
                        f'Malformed IPv{str(version)} association set. Expected '
                        f'a dict, got {type(association_set)}: '
                        f'{str(association_set)}')
                continue

            if version == 4:
                cidr_block_state = association_set.get('CidrBlockState')
            else:
                cidr_block_state = association_set.get('Ipv6CidrBlockState')

            if not (cidr_block_state and isinstance(cidr_block_state, dict)):
                if cidr_block_state:
                    logger.warning(
                        f'Malformed IPv{str(version)} CIDR block state. Expected '
                        f'a dict, got {type(cidr_block_state)}:'
                        f'{str(cidr_block_state)}')
                state = None
                status = None
                border_group = None
                ipv6_pool = None
            else:
                state = cidr_block_state.get('State')
                if state and state not in CIDR_BLOCK_STATE:
                    logger.error(
                        f'New field found in CIDR block state: '
                        f'{str(state)} not in {CIDR_BLOCK_STATE}')
                    state = None
                status = cidr_block_state.get('StatusMessage')
                border_group = cidr_block_state.get('NetworkBorderGroup')
                ipv6_pool = cidr_block_state.get('Ipv6Pool')

            assoc_set = AWSCidrBlockAssociationSet(
                association_id=association_set.get('AssociationId'),
                cidr_block=association_set.get('CidrBlock'),
                cidr_block_state=state,
                cidr_block_status=status,
                network_border_group=border_group,
                ipv6_pool=ipv6_pool
            )
            if version == 4:
                device.ipv4_cidr_block_assoc_set.append(assoc_set)
            else:
                device.ipv6_cidr_block_assoc_set.append(assoc_set)
