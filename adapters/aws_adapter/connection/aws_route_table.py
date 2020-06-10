import logging
from typing import Optional


from aws_adapter.connection.structures import AWSDeviceAdapter, AWSRoute, \
    AWSRouteTableAssociation
from aws_adapter.connection.utils import get_paginated_next_token_api

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements
def query_devices_by_client_by_source_route_table(client_data: dict) -> list:
    """
    Use the boto3, EC2 client from the passed *client_data to collect
    data on AWS Route Tables using pagination and yield them back to
    the caller.

    :param client_data: A boto3 client object used to connect to AWS' API
    """
    rt_client = client_data.get('ec2')
    if not rt_client:
        return

    try:
        for route_table_page in get_paginated_next_token_api(rt_client.describe_route_tables):
            if not isinstance(route_table_page, dict):
                raise ValueError(f'Malformed data in describe route tables, '
                                 f'expected a dict, got '
                                 f'{type(route_table_page)}')

            for page in route_table_page.get('RouteTables') or []:
                if not isinstance(page, (dict, list)):
                    raise ValueError(f'Malformed data in route table page, '
                                     f'expected a dict or a list, got '
                                     f'{type(page)}')

                if isinstance(page, list):
                    for list_page in page:
                        yield list_page
                elif isinstance(page, dict):
                    yield page

    except Exception:
        logger.exception(f'Failed to fetch AWS Route Tables.')


# pylint: disable=too-many-nested-blocks, inconsistent-return-statements
# pylint: disable=too-many-locals
def parse_raw_data_inner_route_table(
        device: AWSDeviceAdapter,
        rt_data_raw: dict,
        generic_resources: dict) -> Optional[AWSDeviceAdapter]:
    """
    Take the passed *rt_data_raw and add it to the AWSDeviceAdapter object
    before returning the object to the caller. This is used only if the
    user would like for route tables to be a device.

    :param device: The AWSDeviceAdapter object
    :param rt_data_raw: The raw data pulled from AWS that is used to
    populate the *device
    :param generic_resources: A dict containing generic information.
    :return device: A populated (optionally) AWSDeviceAdapter object
    """
    # Parse Internet Gateway data
    try:
        rt_id = rt_data_raw.get('RouteTableId')
        if not isinstance(rt_id, str):
            raise ValueError(f'Malformed route table ID in raw data, expected '
                             f'str, got {type(rt_id)}')

        try:
            device.id = rt_id
            device.aws_device_type = 'RouteTable'
            device.cloud_provider = 'AWS'
            device.route_table_id = rt_id

            # route table associations
            try:
                associations = rt_data_raw.get('Associations')
                if not isinstance(associations, list):
                    raise ValueError(f'Malformed route table associations'
                                     f'expected list, got {type(associations)}')

                assoc_list = list()
                for association in associations:
                    if not isinstance(association, dict):
                        raise ValueError(f'Malformed association, expected a '
                                         f'dict, got {type(association)}')

                    association_state = association.get('AssociationState') or {}
                    if not isinstance(association_state, dict):
                        logger.warning(f'Malformed association state, '
                                       f'expected a dict, got '
                                       f'{type(association_state)}')
                        association_state = {}

                    assoc = AWSRouteTableAssociation(
                        main=association.get('Main'),
                        association_id=association.get('RouteTableAssociationId'),
                        route_table_id=association.get('RouteTableId'),
                        subnet_id=association.get('SubnetId'),
                        gateway_id=association.get('GatewayId'),
                        state=association_state.get('State'),
                        status_message=association_state.get('StatusMessage')
                    )
                    assoc_list.append(assoc)
                device.route_table_associations = assoc_list
            except Exception:
                logger.exception(f'Could not process route table '
                                 f'associations: {rt_data_raw}')

            device.route_table_owner_id = rt_data_raw.get('OwnerId')

            # propagating virtual gateways
            try:
                vgws = rt_data_raw.get('PropagatingVgws')
                if not isinstance(vgws, list):
                    raise ValueError(f'Malformed propagating VGWs, '
                                     f'expected list, got {type(vgws)}')

                vgws_list = list()
                for vgw in vgws:
                    if not isinstance(vgw, dict):
                        raise ValueError(f'Malformed VGW, expected dict, '
                                         f'got {type(vgw)}')

                    gateway_id = vgw.get('GatewayId')
                    if isinstance(gateway_id, str):
                        vgws_list.append(gateway_id)

                device.route_table_propagating_vgws.extend(vgws_list)
            except Exception:
                logger.exception(f'Could not process propagating vgws: '
                                 f'{rt_data_raw}')

            # routes
            try:
                routes = rt_data_raw.get('Routes')
                if not isinstance(routes, list):
                    raise ValueError(f'Malformed routes, expected a list, '
                                     f'got {type(routes)}')

                routes_list = list()
                for route in routes:
                    if not isinstance(route, dict):
                        raise ValueError(f'Malformed routes, expected '
                                         f'a dict, got {type(route)}')

                    rt = AWSRoute(
                        destination_cidr=route.get('DestinationCidrBlock'),
                        destination_ipv6_cidr=route.get('DestinationIpv6CidrBlock'),
                        destination_prefix_list_id=route.get('DestinationPrefixListId'),
                        egress_only_igw_id=route.get('EgressOnlyInternetGatewayId'),
                        gateway_id=route.get('GatewayId'),
                        instance_id=route.get('InstanceId'),
                        instance_owner_id=route.get('InstanceOwnerId'),
                        nat_gateway_id=route.get('NatGatewayId'),
                        transit_gateway_id=route.get('TransitGatewayId'),
                        local_gateway_id=route.get('LocalGatewayId'),
                        network_interface_id=route.get('NetworkInterfaceId'),
                        origin=route.get('Origin'),
                        state=route.get('State'),
                        vpc_peering_connection_id=route.get('VpcPeeringConnectionId'),
                    )
                    routes_list.append(rt)
                device.routes = routes_list
            except Exception:
                logger.exception(f'Could not process routes: {rt_data_raw}')

            try:
                tags = rt_data_raw.get('Tags')
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
                    device.name = rt_id

            except Exception:
                logger.exception(f'Could not parse tags: {rt_data_raw}')

            device.vpc_id = rt_data_raw.get('VpcId')

            device.set_raw(rt_data_raw)
            return device
        except Exception:
            logger.exception(f'Problem parsing Route Table: {rt_data_raw}')

    except Exception:
        logger.exception(f'No ID found for Route Table {rt_data_raw}')


def populate_route_tables(device, route_tables: list):
    """
    This function is used when we do not want to create a route_table
    device, but instead are looking to enrich another AWS resource's
    dataset.

    :param device: A DeviceAdapter object
    :param route_tables: a list of dictionaries representing the route
    tables present in an account.
    """
    for route_table in route_tables or []:
        if not isinstance(route_table, dict):
            raise ValueError(f'Malformed route table, expected a dict, got '
                             f'{type(route_table)}')

        if not isinstance(route_table.get('vpc_id'), str):
            raise ValueError(f'Malformed VPC ID in data, expected a string, '
                             f'got {type(route_table.get("vpc_id"))}')

        # some resource may not have a vpc_id
        try:
            vpc_id = device.vpc_id
        except Exception:
            vpc_id = ''
            logger.warning(
                f'Device {str(device.id)} does not have a valid VPC ID')

        if not isinstance(vpc_id, str):
            raise ValueError(f'Malformed VPC ID in device, expected a string, '
                             f'got {type(device.vpc_id)}')

        if route_table.get('vpc_id') == vpc_id:
            try:
                rt_id = route_table.get('route_table_id')
                if not isinstance(rt_id, str):
                    raise ValueError(f'Malformed route table ID, expected a '
                                     f'string, got {type(rt_id)}')

                device.route_table_ids.append(rt_id)
            except Exception:
                logger.exception(f'Unable to set VPC route table ID: '
                                 f'{route_table}')

            for association in route_table.get('associations') or []:
                if not isinstance(association, dict):
                    raise ValueError(f'Malformed route table association, '
                                     f'expected a dict, got '
                                     f'{type(association)}')

                state = None
                if isinstance(association.get('associations'), dict):
                    state = association.get('associations').get('association_state')

                if state is not None:
                    state = str(state)

                try:
                    device.route_table_associations.append(
                        AWSRouteTableAssociation(
                            main=association.get('main_route_table'),
                            association_id=association.get('association_id'),
                            subnet_id=association.get('subnet_id'),
                            gateway_id=association.get('gateway_id'),
                            state=state
                        )
                    )
                except Exception:
                    logger.exception(
                        f'Unable to set route table association: {route_table}')

            try:
                propagating_vgws = route_table.get('propagating_vgw') or []
                if not isinstance(propagating_vgws, list):
                    raise ValueError(f'Malformed propagating VGWs data, '
                                     f'expected list, got '
                                     f'{type(propagating_vgws)}')

                # there can be duplicates in propagating_vgws, so using a set
                for gateway in set(propagating_vgws):
                    if not isinstance(gateway, str):
                        raise ValueError(f'Malformed gateway, expected str,'
                                         f' got {type(gateway)}')

                    if gateway not in device.route_table_propagating_vgws:
                        device.route_table_propagating_vgws.append(gateway)
            except Exception:
                logger.exception(
                    f'Unable to set propagating VGWs: {route_table}')

            for route in route_table.get('routes') or []:
                if not isinstance(route, dict):
                    raise ValueError(f'Route is not a dict: {type(route)}')

                try:
                    device.routes.append(
                        AWSRoute(
                            route_table_id=route_table.get('route_table_id'),
                            destination_cidr=route.get('destination_ipv4_cidr'),
                            destination_ipv6_cidr=route.get('destination_ipv6_cidr'),
                            destination_prefix_list_id=route.get('destination_prefix_list_id'),
                            egress_only_igw_id=route.get('egress_only_igw_id'),
                            gateway_id=route.get('gateway_id'),
                            instance_id=route.get('instance_id'),
                            instance_owner_id=route.get('instance_owner_id'),
                            nat_gateway_id=route.get('nat_gateway_id'),
                            transit_gateway_id=route.get('transit_gateway_id'),
                            local_gateway_id=route.get('local_gateway_id'),
                            network_interface_id=route.get('network_interface_id'),
                            origin=route.get('origin'),
                            state=route.get('state'),
                            vpc_peering_connection_id=route.get('vpc_peering_connection_id'),
                        )
                    )
                except Exception:
                    logger.exception(f'Unable to build routes: {route_table}')

            device.route_table_name = route_table.get('route_table_id')

            try:
                tags = route_table.get('tags')
                if not isinstance(tags, list):
                    raise ValueError(f'Malformed tags, exptected a list, got '
                                     f'{type(tags)}')

                for tag in tags:
                    if not isinstance(tag, dict):
                        raise ValueError(f'Malformed tag, expected a dict, '
                                         f'got {type(tag)}')

                    for key, value in tag.items():
                        device.add_aws_ec2_tag(key=key, value=value)
                        device.add_key_value_tag(key, value)

                    if tag.get('Name'):
                        device.route_table_name = tag.get('Name')
                        continue
            except Exception:
                logger.exception(
                    f'Could not process tags: {route_table}')
