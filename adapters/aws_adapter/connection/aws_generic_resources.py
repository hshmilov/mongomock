# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements, too-many-locals
import logging

from aws_adapter.connection.utils import get_paginated_marker_api, get_paginated_next_token_api

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-locals, too-many-branches, too-many-statements
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

    # pylint: disable=too-many-nested-blocks
    route_tables = list()
    try:
        for rt_page in ec2_client_data.get_paginator('describe_route_tables').paginate():
            if not isinstance(rt_page, dict):
                raise ValueError(f'Malformed route table page, expected dict, '
                                 f'got {type(rt_page)}')

            route_tables_data = rt_page.get('RouteTables')
            if not isinstance(route_tables_data, list):
                raise ValueError(f'Route table data is malformed: '
                                 f'{type(route_tables_data)}')

            for route_table_raw in (route_tables_data or []):
                if not isinstance(route_table_raw, dict):
                    raise ValueError(f'Malformed raw route table data, expected '
                                     f'dict, got {type(route_table_raw)} ')

                route_table_dict = dict()
                route_table_dict['associations'] = list()
                route_table_dict['tags'] = list()

                associations_raw = route_table_raw.get('Associations')
                if not isinstance(associations_raw, list):
                    raise ValueError(f'Route table associations is not a list: '
                                     f'{type(associations_raw)}')

                # get all route table associations
                for association_raw in (associations_raw or []):
                    # NOTE: some fields will not be populated unless the route
                    # table is explicitly associated with a VPC/Subnet. By
                    # default, they are not.
                    if not isinstance(association_raw, dict):
                        raise ValueError(f'Association data is not a dict: '
                                         f'{type(association_raw)}')
                    association = dict()
                    association['main_route_table'] = association_raw.get('Main')
                    association['association_id'] = association_raw.get('RouteTableAssociationId')
                    association['route_table_id'] = association_raw.get('RouteTableId')
                    association['subnet_id'] = association_raw.get('SubnetId')
                    association['gateway_id'] = association_raw.get('GatewayId')

                    association_state = association_raw.get('AssociationState')
                    if isinstance(association_state, dict):
                        association['association_state'] = association_state.get('State')
                        association['association_state_status'] = association_state.get('StatusMessage')

                    route_table_dict['associations'].append(association)

                # get all propagating virtual gateways
                try:
                    vgws = list()
                    propagating_vgws = route_table_raw.get('PropagatingVgws')
                    if isinstance(propagating_vgws, list):
                        for vgw in propagating_vgws:
                            if not isinstance(vgw, dict):
                                raise ValueError(f'VGW is not a dict: {type(vgw)}')

                            vgws.append(vgw.get('GatewayId'))

                        route_table_dict['propagating_vgw'] = vgws
                    else:
                        logger.warning(f'Malformed propagating VGWs. Expected '
                                       f'a list, got {type(propagating_vgws)}: '
                                       f'{str(propagating_vgws)}')
                except Exception:
                    logger.exception(f'Unable to populate propagating VGWs: '
                                     f'{str(route_table_raw.get("PropagatingVgws"))}')

                route_table_dict['route_table_id'] = route_table_raw.get('RouteTableId')

                # get all routes
                try:
                    route_table_dict['routes'] = list()
                    route_table_routes = route_table_raw.get('Routes')
                    if isinstance(route_table_routes, list):
                        for route_raw in route_table_routes:
                            if not isinstance(route_raw, dict):
                                raise ValueError(f'Route raw data is not a dict:'
                                                 f'{type(route_raw)}')
                            route = dict()
                            route['destination_ipv4_cidr'] = route_raw.get('DestinationCidrBlock')
                            route['destination_ipv6_cidr'] = route_raw.get('DestinationIpv6CidrBlock')
                            route['destination_prefix_list_id'] = route_raw.get('DestinationPrefixListId')
                            route['egress_only_igw_id'] = route_raw.get('EgressOnlyInternetGatewayId')
                            route['gateway_id'] = route_raw.get('GatewayId')
                            route['instance_id'] = route_raw.get('InstanceId')
                            route['instance_owner_id'] = route_raw.get('InstanceOwnerId')
                            route['nat_gateway_id'] = route_raw.get('NatGatewayId')
                            route['transit_gateway_id'] = route_raw.get('TransitGatewayId')
                            route['local_gateway_id'] = route_raw.get('LocalGatewayId')
                            route['network_interface_id'] = route_raw.get('NetworkInterfaceId')
                            route['origin'] = route_raw.get('Origin')
                            route['state'] = route_raw.get('State')
                            route['vpc_peering_connection_id'] = route_raw.get('VpcPeeringConnectionId')
                            route_table_dict['routes'].append(route)
                except Exception:
                    logger.exception(f'Unable to populate route table routes:'
                                     f'{str(route_table_raw.get("Routes"))}')

                for tag in (route_table_raw.get('Tags') or []):
                    if not isinstance(tag, dict):
                        logger.warning(f'Error while parsing route table tag '
                                       f'{str(tag)}')
                        continue
                    route_table_dict['tags'].append(tag)

                route_table_dict['vpc_id'] = route_table_raw.get('VpcId')
                route_table_dict['owner_id'] = route_table_raw.get('OwnerId')

                route_tables.append(route_table_dict)

    except Exception:
        logger.exception('Could not acquire AWS Route Tables')

    return {
        'vpcs': described_vpcs,
        'security_groups': security_groups_dict,
        'subnets': subnets_dict,
        'route_tables': route_tables,
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
