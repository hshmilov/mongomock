import functools
import logging
from typing import Tuple, Optional, Dict

from aws_adapter.connection.structures import AWSDeviceAdapter, SSMInfo, SSMComplianceSummary, AwsSSMSchemas
from aws_adapter.connection.utils import get_paginated_next_token_api
from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements, too-many-locals
def query_devices_by_client_by_source_ssm(client_data: dict) -> dict:
    if client_data.get('ssm') is not None:
        try:
            all_instances = dict()
            ssm = client_data['ssm']
            # First, get all instance_id id's that have ssm
            for ssm_page in get_paginated_next_token_api(ssm.describe_instance_information):
                for instance_information in (ssm_page.get('InstanceInformationList') or []):
                    unique_instance_id = instance_information.get('InstanceId')
                    if unique_instance_id:
                        all_instances[unique_instance_id] = instance_information

            # Next, get all schemas.
            schemas_names = []
            for schema_page in get_paginated_next_token_api(ssm.get_inventory_schema):
                for schema_raw in schema_page['Schemas']:
                    schema_name = schema_raw.get('TypeName')
                    if schema_name:
                        schemas_names.append(schema_name)

            # Next, get all patch group to patch baseline mappings
            patch_groups_to_patch_baseline = dict()
            try:
                for patch_group_page in get_paginated_next_token_api(ssm.describe_patch_groups):
                    for patch_group_page_mapping in patch_group_page['Mappings']:
                        try:
                            patch_group_name = patch_group_page_mapping['PatchGroup']
                            patch_groups_to_patch_baseline[patch_group_name] = patch_group_page_mapping
                        except Exception:
                            logger.exception(f'Can not parse patch group page mapping {patch_group_page_mapping}')
            except Exception:
                logger.exception(f'Problem getting patches')

            # Next, get all compliance summaries
            resource_id_to_compliance_summaries = dict()
            try:
                for compliance_summary_page in get_paginated_next_token_api(ssm.list_resource_compliance_summaries):
                    for resource_compliance_summary in compliance_summary_page['ResourceComplianceSummaryItems']:
                        try:
                            resource_id = resource_compliance_summary.get('ResourceId')
                            resource_type = resource_compliance_summary.get('ResourceType')
                            if resource_type == 'ManagedInstance' and resource_id:
                                if resource_id not in resource_id_to_compliance_summaries:
                                    resource_id_to_compliance_summaries[resource_id] = []
                                resource_id_to_compliance_summaries[resource_id].append(resource_compliance_summary)
                        except Exception:
                            logger.exception(f'Can not parse patch resource compliance {resource_compliance_summary}')
            except Exception:
                logger.exception(f'Problem getting complaince summary')

            all_patches_general_info = {}
            try:
                for patch_page in get_paginated_next_token_api(ssm.describe_available_patches):
                    for patch_raw in (patch_page.get('Patches') or []):
                        if patch_raw.get('KbNumber'):
                            all_patches_general_info[patch_raw.get('KbNumber')] = patch_raw
                        elif patch_raw.get('MsrcNumber'):
                            all_patches_general_info[patch_raw.get('MsrcNumber')] = patch_raw
            except Exception:
                pass

            for iid, iid_basic_data in all_instances.items():
                raw_instance = dict()
                raw_instance['basic_data'] = iid_basic_data
                # Next, pull the following schemas
                for schema in AwsSSMSchemas:
                    try:
                        entries = []
                        for schema_page in get_paginated_next_token_api(
                                functools.partial(ssm.list_inventory_entries, InstanceId=iid, TypeName=schema.value)
                        ):
                            entries.extend(schema_page.get('Entries') or [])

                        if entries:
                            raw_instance[schema.value] = entries
                    except Exception:
                        logger.exception(f'Problem querying info of schema {schema.value} for device {iid}')

                # Also, pull the patches for ths instance
                all_patches = []
                try:
                    for patch_page in get_paginated_next_token_api(
                            functools.partial(ssm.describe_instance_patches, InstanceId=iid)
                    ):
                        all_patches.extend(patch_page.get('Patches') or [])

                    if all_patches:
                        raw_instance['patches'] = all_patches
                except Exception:
                    logger.exception(f'Problem getting patches')

                # Pull the tags for this resource. This does not support pagination.
                try:
                    if iid.startswith('mi-'):
                        raw_tags = ssm.list_tags_for_resource(
                            ResourceType='ManagedInstance', ResourceId=iid)['TagList']
                    else:
                        raw_tags = client_data.get('ec2').describe_tags(
                            Filters=[{'Name': 'resource-id', 'Values': [iid]}]
                        )['Tags']

                    raw_instance['tags'] = {item.get('Key'): item.get('Value') for item in raw_tags}
                except Exception:
                    logger.exception(f'Problem getting ssm tags')

                # Get compliance summaries
                raw_instance['compliance_summary'] = resource_id_to_compliance_summaries.get(iid)

                yield raw_instance, patch_groups_to_patch_baseline, all_patches_general_info
        except Exception:
            logger.exception(f'Problem fetching data for ssm')


def parse_raw_data_inner_ssm(
        device: AWSDeviceAdapter,
        device_raw_data_all: Tuple[Dict[str, Dict], Dict[str, Dict], Dict[str, dict]],
        generic_resources: dict
) -> Optional[AWSDeviceAdapter]:
    device_raw_data, patch_group_to_patch_baseline_mapping, all_patches_general_info = device_raw_data_all
    basic_data = device_raw_data.get('basic_data')
    if not basic_data:
        logger.warning('Wierd device, no basic data!')
        return None

    try:
        device.id = 'ssm-' + basic_data['InstanceId']
        device.cloud_provider = 'AWS'
        device.cloud_id = basic_data['InstanceId']
        if basic_data.get('IPAddress'):
            device.add_nic(ips=[basic_data['IPAddress']])

        # Parse ssm data
        ssm_data = SSMInfo()
        ssm_data.ping_status = basic_data.get('PingStatus')
        ssm_data.last_ping_date = parse_date(basic_data.get('LastPingDateTime'))
        # Do not set device.last_seen! otherwise filtering devices will not work without 'Include outdated adapter...'
        device.ssm_data_last_seen = parse_date(basic_data.get('LastPingDateTime'))
        ssm_data.last_seen = parse_date(basic_data.get('LastPingDateTime'))
        ssm_data.agent_version = basic_data.get('AgentVersion')
        try:
            ssm_data.is_latest_version = bool(basic_data.get('IsLatestVersion'))
        except Exception:
            logger.exception(f'Problem parsing if ssm agent is latest version')

        device.figure_os((basic_data.get('PlatformName') or '') + ' ' + (basic_data.get('PlatformVersion') or ''))
        ssm_data.activation_id = basic_data.get('ActivationId')
        ssm_data.registration_date = parse_date(basic_data.get('RegistrationDate'))
        resource_type = basic_data.get('ResourceType') or ''
        if 'ec2' in resource_type.lower():
            device.aws_device_type = 'EC2'
        elif 'managed' in resource_type.lower():
            device.aws_device_type = 'Managed'

        hostname = basic_data.get('ComputerName') or ''
        device.hostname = basic_data.get('ComputerName')
        ssm_data.association_status = basic_data.get('AssociationStatus')
        ssm_data.last_association_execution_date = parse_date(
            basic_data.get('LastAssociationExecutionDate'))
        ssm_data.last_successful_association_execution_date = parse_date(
            basic_data.get('LastSuccessfulAssociationExecutionDate'))

        patch_group = (device_raw_data.get('tags') or {}).get('Patch Group')

        try:
            for tag_key, tag_value in (device_raw_data.get('tags') or {}).items():
                device.add_aws_ec2_tag(key=tag_key, value=tag_value)
        except Exception:
            logger.exception(f'Could not populate ssm tags')

        ssm_data.patch_group = patch_group

        patch_baseline_info = (patch_group_to_patch_baseline_mapping.get(patch_group) or {})
        patch_baseline_identity = patch_baseline_info.get('BaselineIdentity') or {}
        if patch_baseline_identity:
            ssm_data.baseline_id = patch_baseline_identity.get('BaselineId')
            ssm_data.baseline_name = patch_baseline_identity.get('BaselineName')
            ssm_data.baseline_description = patch_baseline_identity.get('BaselineDescription')

        # Compliance
        compliance_summary = device_raw_data.get('compliance_summary')
        if compliance_summary:
            try:
                for compliance_item_summary in compliance_summary:
                    execution_summary = compliance_item_summary.get('ExecutionSummary') or {}

                    compliant_summary = compliance_item_summary.get('CompliantSummary') or {}
                    compliant_severity_summary = compliant_summary.get('SeveritySummary')

                    non_compliant_summary = compliance_item_summary.get('NonCompliantSummary') or {}
                    non_compliant_severity_summary = non_compliant_summary.get('SeveritySummary')

                    compliance_type = compliance_item_summary.get('ComplianceType')
                    new_compliance = (
                        SSMComplianceSummary(
                            status=compliance_item_summary.get('Status'),
                            overall_severity=compliance_item_summary.get('OverallSeverity'),
                            last_execution=parse_date(execution_summary.get('ExecutionTime')),
                            compliant_count=compliant_summary.get('CompliantCount'),
                            compliant_critical_count=compliant_severity_summary.get('CriticalCount'),
                            compliant_high_count=compliant_severity_summary.get('HighCount'),
                            compliant_medium_count=compliant_severity_summary.get('MediumCount'),
                            compliant_low_count=compliant_severity_summary.get('LowCount'),
                            compliant_informational_count=compliant_severity_summary.get('InformationalCount'),
                            compliant_unspecified_count=compliant_severity_summary.get('UnspecifiedCount'),
                            non_compliant_count=non_compliant_summary.get('NonCompliantCount'),
                            non_compliant_critical_count=non_compliant_severity_summary.get('CriticalCount'),
                            non_compliant_high_count=non_compliant_severity_summary.get('HighCount'),
                            non_compliant_medium_count=non_compliant_severity_summary.get('MediumCount'),
                            non_compliant_low_count=non_compliant_severity_summary.get('LowCount'),
                            non_compliant_informational_count=non_compliant_severity_summary.get('InformationalCount'),
                            non_compliant_unspecified_count=non_compliant_severity_summary.get('UnspecifiedCount')
                        )
                    )
                    if str(compliance_type).lower() == 'patch':
                        ssm_data.patch_compliance_summaries.append(new_compliance)
                    elif str(compliance_type).lower() == 'association':
                        ssm_data.association_compliance_summaries.append(new_compliance)
                    else:
                        logger.error(f'Error parsing unknown compliance type {compliance_type}')
            except Exception:
                logger.exception(f'Problem parsing compliance summary')

        applications = device_raw_data.get(AwsSSMSchemas.Application.value)
        if isinstance(applications, list):
            for app_data in applications:
                try:
                    device.add_installed_software(
                        architecture=app_data.get('Architecture'),
                        name=app_data.get('Name'),
                        version=app_data.get('Version'),
                        vendor=app_data.get('Publisher'),
                        publisher=app_data.get('Publisher')
                    )
                except Exception:
                    logger.exception(f'Failed to add application {app_data} for host {hostname}')

        network = device_raw_data.get(AwsSSMSchemas.Network.value)
        dns_servers = set()
        dhcp_servers = set()
        if isinstance(network, list):
            for network_interface in network:
                try:
                    ips = []
                    ipv4_raw = network_interface.get('IPV4')
                    ipv6_raw = network_interface.get('IPV6')
                    if ipv4_raw:
                        if isinstance(ipv4_raw, str):
                            ipv4_raw = [ipv4.strip() for ipv4 in ipv4_raw.split(',')]
                        ips.extend(ipv4_raw)

                    if ipv6_raw:
                        if isinstance(ipv6_raw, str):
                            ipv6_raw = [ipv6.strip() for ipv6 in ipv6_raw.split(',')]
                        ips.extend(ipv6_raw)
                    device.add_nic(
                        mac=network_interface.get('MacAddress'),
                        ips=ips,
                        name=network_interface.get('Name'),
                        gateway=network_interface.get('Gateway')
                    )

                    dns_s = network_interface.get('DNSServer')
                    if isinstance(dns_s, str):
                        dns_servers.add(dns_s)

                    dhcp_s = network_interface.get('DHCPServer')
                    if isinstance(dhcp_s, str):
                        dhcp_servers.add(dhcp_s)
                except Exception:
                    logger.exception(f'Failed to add network interface {network_interface} for host {hostname}')

        if dns_servers:
            device.dns_servers = list(dns_servers)

        if dhcp_servers:
            device.dhcp_servers = list(dhcp_servers)

        services = device_raw_data.get(AwsSSMSchemas.Service.value)
        if isinstance(services, list):
            for service_raw in services:
                try:
                    device.add_service(
                        name=service_raw.get('Name'),
                        display_name=service_raw.get('DisplayName'),
                        status=service_raw.get('Status')
                    )
                except Exception:
                    logger.exception(f'Failed to add service {service_raw} for host {hostname}')

        all_patches = device_raw_data.get('patches')
        if isinstance(all_patches, list):
            for pc_raw in all_patches:
                try:
                    # https://docs.aws.amazon.com/systems-manager/latest/userguide/about-patch-compliance.html
                    patch_state = pc_raw.get('State')
                    if not patch_state:
                        continue
                    if 'installed' in str(patch_state).lower():
                        device.add_security_patch(
                            security_patch_id=pc_raw.get('Title') + ' ' + pc_raw.get('KBId'),
                            classification=pc_raw.get('Classification'),
                            severity=pc_raw.get('Severity'),
                            state=patch_state,
                            installed_on=parse_date(pc_raw.get('InstalledTime'))
                        )
                    else:
                        # could be 'missing', 'failed', or 'not_applicable', in all cases it is not installed
                        kb_id = pc_raw.get('KBId')
                        device.add_available_security_patch(
                            title=pc_raw.get('Title') + ' ' + pc_raw.get('KBId'),
                            kb_article_ids=[kb_id] if kb_id else None,
                            state=patch_state,
                            severity=pc_raw.get('Severity'),
                            publish_date=parse_date((all_patches_general_info.get(kb_id) or {}).get('ReleaseDate'))
                        )
                except Exception:
                    logger.exception(f'Failed to add patch compliance {pc_raw} for host {hostname}')

        device.ssm_data = ssm_data
        device.set_raw(device_raw_data)
        return device
    except Exception:
        logger.exception(f'Problem parsing SSM device')
