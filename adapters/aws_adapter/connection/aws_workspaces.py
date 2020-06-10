import logging
from typing import Optional

from aws_adapter.connection.aws_route_table import populate_route_tables
from aws_adapter.connection.structures import AWSDeviceAdapter, AWSWorkspaceDevice
from aws_adapter.connection.utils import get_paginated_next_token_api
from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements
def query_devices_by_client_by_source_workspaces(client_data: dict):
    if client_data.get('workspaces') is not None:
        try:
            errors_reported = []
            workspaces_client = client_data.get('workspaces')

            workspace_directories = dict()
            try:
                for workspace_directory_page in get_paginated_next_token_api(
                        workspaces_client.describe_workspace_directories
                ):
                    for workspace_directory_raw in (workspace_directory_page.get('Directories') or []):
                        directory_id = workspace_directory_raw.get('DirectoryId')
                        if directory_id:
                            workspace_directories[directory_id] = workspace_directory_raw
            except Exception:
                if 'workspace_directories' not in errors_reported:
                    errors_reported.append('workspace_directories')
                    logger.exception(f'Problem while fetching workspace directories')

            workspace_connection_status = dict()
            try:
                for workspace_connection_statuses_page in get_paginated_next_token_api(
                        workspaces_client.describe_workspaces_connection_status):
                    for workspace_connection_status_raw in (workspace_connection_statuses_page.get(
                            'WorkspacesConnectionStatus') or []):
                        workspace_id = workspace_connection_status_raw.get('WorkspaceId')
                        if workspace_id:
                            workspace_connection_status[workspace_id] = workspace_connection_status_raw
            except Exception:
                if 'workspace_connection_status' not in errors_reported:
                    errors_reported.append('workspace_connection_status')
                    logger.exception(f'Problem while fetching workspace_connection_status')

            for workspaces_page in get_paginated_next_token_api(workspaces_client.describe_workspaces):
                for workspace_raw in (workspaces_page.get('Workspaces') or []):
                    workspace_id = workspace_raw.get('WorkspaceId')
                    if workspace_id:
                        try:
                            workspace_raw['tags'] = workspaces_client.describe_tags(
                                ResourceId=workspace_id
                            )['TagList']
                        except Exception:
                            if 'workspace_tags' not in errors_reported:
                                errors_reported.append('workspace_tags')
                                logger.exception(f'Problem while fetching '
                                                 f'workspace_tags')

                        if workspace_raw.get('DirectoryId'):
                            workspace_raw['workspace_directory'] = workspace_directories.get(
                                workspace_raw.get('DirectoryId')
                            )

                        # get the VPC ID from the Subnet ID
                        subnet_id = workspace_raw.get('SubnetId')
                        if isinstance(subnet_id, str):
                            try:
                                ec2_client = client_data.get('ec2')
                                try:
                                    subnets = ec2_client.describe_subnets(
                                        SubnetIds=[subnet_id])
                                    if not isinstance(subnets, dict):
                                        raise ValueError(f'Malformed subnet. '
                                                         f'Expected a dict, got '
                                                         f'{type(subnets)}: '
                                                         f'{str(subnets)}')

                                    for subnet in subnets.get('Subnets') or []:
                                        if isinstance(subnet, dict):
                                            if subnet.get('SubnetId') == subnet_id:
                                                workspace_raw['vpc_id'] = subnet.get('VpcId')
                                                break
                                        else:
                                            logger.warning(
                                                f'Malformed subnet. '
                                                f'Expected a dict, got '
                                                f'{type(subnet)}: '
                                                f'{str(subnet)}')

                                except Exception:
                                    logger.exception(f'Unable to extract '
                                                     f'VPC ID from Subnet ID: '
                                                     f'{subnet_id}')
                            except Exception:
                                logger.exception(f'Could not get a boto3 ec2 '
                                                 f'client')

                        if workspace_connection_status.get(workspace_id):
                            workspace_raw['workspace_connection_status'] = workspace_connection_status.get(
                                workspace_id
                            )

                        yield workspace_raw

        except Exception:
            logger.exception(f'Problem fetching information about Workspaces')

# pylint: disable=too-many-statements


def parse_raw_data_inner_workspaces(
        device: AWSDeviceAdapter,
        workspace_raw: dict,
        generic_resources: dict,
        options: dict
) -> Optional[AWSDeviceAdapter]:
    # Parse Workspaces
    subnets_by_id = generic_resources.get('subnets') or {}
    route_tables = generic_resources.get('route_tables') or []

    try:
        workspace_id = workspace_raw['WorkspaceId']

        device.id = workspace_id
        device.aws_device_type = 'Workspace'
        device.cloud_provider = 'AWS'

        directory_data = workspace_raw.get('workspace_directory') or {}
        workspace_properties = (workspace_raw.get('WorkspaceProperties') or {})

        user_volume_encryption_enabled = workspace_raw.get('UserVolumeEncryptionEnabled')
        root_volume_encryption_enabled = workspace_raw.get('RootVolumeEncryptionEnabled')
        user_volume_size_gib = workspace_properties.get('UserVolumeSizeGib')
        root_volume_size_gib = workspace_properties.get('RootVolumeSizeGib')

        if user_volume_size_gib is not None or user_volume_encryption_enabled is not None:
            try:
                device.add_hd(
                    total_size=user_volume_size_gib,
                    is_encrypted=user_volume_encryption_enabled,
                    description='User Volume'
                )
            except Exception:
                logger.exception(f'Can not add user volume information')

        if root_volume_size_gib is not None or root_volume_encryption_enabled is not None:
            try:
                device.add_hd(
                    total_size=root_volume_size_gib,
                    is_encrypted=root_volume_encryption_enabled,
                    description='Root Volume'
                )
            except Exception:
                logger.exception(f'Can not add root volume information')

        workspace_connection_status = workspace_raw.get('workspace_connection_status') or {}
        workspace_connection_status_timestamp = None
        try:
            workspace_connection_status_timestamp = parse_date(
                workspace_connection_status.get('ConnectionStateCheckTimestamp')
            )
            device.last_seen = workspace_connection_status_timestamp
        except Exception:
            pass

        device.workspace_data = AWSWorkspaceDevice(
            workspace_id=workspace_raw.get('WorkspaceId'),
            directory_id=workspace_raw.get('DirectoryId'),
            directory_alias=directory_data.get('Alias'),
            directory_name=directory_data.get('DirectoryName'),
            username=workspace_raw.get('UserName'),
            state=workspace_raw.get('State'),
            bundle_id=workspace_raw.get('BundleId'),
            error_message=workspace_raw.get('ErrorMessage'),
            error_code=workspace_raw.get('ErrorCode'),
            volume_encryption_key=workspace_raw.get('VolumeEncryptionKey'),
            running_mode=workspace_properties.get('RunningMode'),
            running_mode_auto_stop_timeout_in_minutes=workspace_properties.get(
                'RunningModeAutoStopTimeoutInMinutes'
            ),
            compute_type_name=workspace_properties.get('ComputeTypeName'),
            user_volume_encryption_enabled=user_volume_encryption_enabled,
            root_volume_encryption_enabled=root_volume_encryption_enabled,
            user_volume_size_gib=user_volume_size_gib,
            root_volume_size_gib=root_volume_size_gib,
            connection_state=workspace_connection_status.get('ConnectionState'),
            connection_state_check_timestamp=workspace_connection_status_timestamp,
            last_known_user_connection_timestamp=parse_date(
                workspace_connection_status.get('LastKnownUserConnectionTimestamp')
            )
        )

        if workspace_raw.get('IpAddress'):
            device.add_nic(ips=[workspace_raw.get('IpAddress')])

        device.subnet_id = workspace_raw.get('SubnetId')
        device.subnet_name = (subnets_by_id.get(workspace_raw.get('SubnetId')) or {}).get('name')
        device.vpc_id = workspace_raw.get('VpcId')

        device.hostname = workspace_raw.get('ComputerName')
        if workspace_raw.get('UserName'):
            device.last_used_users = [workspace_raw.get('UserName')]

        try:
            tags_dict = {i['Key']: i['Value'] for i in (workspace_raw.get('tags') or {})}
            for key, value in tags_dict.items():
                device.add_aws_ec2_tag(key=key, value=value)
                device.add_key_value_tag(key, value)
        except Exception:
            logger.exception(f'Problem parsing tags')

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

        device.set_raw(workspace_raw)
        return device
    except Exception:
        logger.exception(f'Problem parsing workspace')
