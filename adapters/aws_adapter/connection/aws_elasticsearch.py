import json
import logging
from typing import Optional

from aws_adapter.connection.structures import AWSDeviceAdapter, \
    AWSElasticsearchEndpoint, AWSElasticsearchEBSOption, \
    AWSElasticsearchSnapshotOption, AWSElasticsearchCognitoOption, \
    AWSElasticsearchEncryptionOption, AWSElasticsearchAdvancedOption, \
    AWSElasticsearchServiceSoftwareOption, AWSElasticsearchEndpointOption, \
    AWSElasticsearchSecurityOption, AWSElasticsearchVPCOptions, \
    AWSElasticsearchLogOptions, AWSElasticsearchClusterConfig, AWSIAMPolicy, \
    AWSIAMPolicyPermission, AWSIAMPolicyPrincipal
from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=invalid-name, too-many-nested-blocks
def query_devices_by_client_by_source_elasticsearch(client_data: dict):
    if client_data.get('es') is not None:
        try:
            es_client = client_data.get('es')

            # get a list of the discovered cluster names
            response = es_client.list_domain_names()
            domains_discovered = response.get('DomainNames')
            if domains_discovered and isinstance(domains_discovered, list):
                domains = [domain.get('DomainName') for domain in domains_discovered]
                try:
                    response = es_client.describe_elasticsearch_domains(
                        DomainNames=domains)
                    if isinstance(response, dict) and isinstance(
                            response.get('DomainStatusList'), list):

                        for domain_status in response.get('DomainStatusList'):
                            if isinstance(domain_status, dict):
                                is_public = check_security_groups(
                                    client_data,
                                    domain_status)

                                domain_status['IsPublic'] = is_public

                                yield domain_status
                            else:
                                logger.warning(f'Malformed domain. Expected a '
                                               f'dict, got {type(domain_status)}: '
                                               f'{str(domain_status)}')
                                continue
                    else:
                        logger.warning(f'Malformed response from describe '
                                       f'Elasticsearch domains: {str(response)}')
                        return
                except Exception:
                    logger.exception(f'Unable to parse Elasticsearch domains: '
                                     f'{str(domains_discovered)}')
                    return
            else:
                if domains_discovered is not None and len(domains_discovered) > 0:
                    logger.warning(f'Malformed domains discovered. Expected a '
                                   f'list, got {type(domains_discovered)}: '
                                   f'{str(domains_discovered)}')
        except Exception:
            logger.exception(f'Problem fetching information about Elasticsearch:')


# pylint: disable=too-many-locals, too-many-branches,
# pylint: disable=too-many-statements, too-many-nested-blocks
def parse_raw_data_inner_elasticsearch(device: AWSDeviceAdapter,
                                       domain: dict,
                                       ) -> Optional[AWSDeviceAdapter]:
    # Parse Elasticsearch domain
    try:
        logger.debug(f'Started parsing Elasticsearch domain: '
                     f'{domain.get("DomainName")}')

        device.aws_device_type = 'Elasticsearch'
        device.cloud_provider = 'AWS'
        device.id = domain.get('DomainId')
        device.es_id = domain.get('DomainId')
        device.name = domain.get('DomainName')
        device.es_name = domain.get('DomainName')
        device.es_arn = domain.get('ARN')
        created = domain.get('Created')
        if isinstance(created, bool):
            device.es_created = created
        deleted = domain.get('Deleted')
        if isinstance(deleted, bool):
            device.es_deleted = deleted
        device.es_endpoint = domain.get('Endpoint')
        device.is_public = domain.get('IsPublic')
        device.es_configured_as_public = False

        new_endpoints = list()
        endpoints = domain.get('Endpoints')
        if isinstance(endpoints, dict):
            # there could be a random and large number of these
            for service, endpoint in endpoints.items():
                service_endpoint = AWSElasticsearchEndpoint(
                    service=service,
                    endpoint=endpoint
                )
                new_endpoints.append(service_endpoint)

            device.es_endpoints = new_endpoints
        else:
            if endpoints is not None:
                logger.warning(f'Malformed Elasticsearch endpoints. Expected a '
                               f'dict, got {type(endpoints)}: {str(endpoints)}')

        processing = domain.get('Processing')
        if isinstance(processing, bool):
            device.es_processing = processing
        upgrade_processing = domain.get('UpgradeProcessing')
        if isinstance(upgrade_processing, bool):
            device.es_upgrade_processing = upgrade_processing
        device.es_version = domain.get('ElasticsearchVersion')

        cluster_config = domain.get('ElasticsearchClusterConfig')
        if cluster_config and isinstance(cluster_config, dict):
            new_cluster_config = AWSElasticsearchClusterConfig(
                instance_type=cluster_config.get('InstanceType'),
                instance_count=cluster_config.get('InstanceCount'),
                dedicated_master_enabled=cluster_config.get('DedicatedMasterEnabled'),
                zone_awareness_enabled=cluster_config.get('ZoneAwarenessEnabled'),
                dedicated_master_type=cluster_config.get('DedicatedMasterType'),
                dedicated_master_count=cluster_config.get('DedicatedMasterCount')
            )
            device.es_cluster_config = new_cluster_config
        else:
            if cluster_config is not None:
                logger.warning(f'Malformed Elasticsearch cluster configuration.'
                               f'Expected a dict, got {type(cluster_config)}: '
                               f'{str(cluster_config)}')

        ebs_options = domain.get('EBSOptions')
        if ebs_options and isinstance(ebs_options, dict):
            new_ebs_options = AWSElasticsearchEBSOption(
                enabled=ebs_options.get('EBSEnabled'),
                volume_type=ebs_options.get('VolumeType'),
                volume_size=ebs_options.get('VolumeSize'),
                iops=ebs_options.get('Iops')
            )
            device.es_ebs_options = new_ebs_options
        else:
            if ebs_options is not None:
                logger.warning(f'Malformed Elasticsearch EBS options. Expected '
                               f'a dict, got {type(ebs_options)}:'
                               f'{str(ebs_options)}')

        access_policies = domain.get('AccessPolicies')
        if access_policies and isinstance(access_policies, str):
            access_policy = json.loads(access_policies)
            if access_policy and isinstance(access_policy, dict):
                version = access_policy.get('Version')
                statements = access_policy.get('Statement')
                if statements and isinstance(statements, list):
                    for statement in statements:
                        permissions = list()
                        if statement and isinstance(statement, dict):
                            permission = AWSIAMPolicyPermission(
                                policy_action=[statement.get('Action')],
                                policy_effect=statement.get('Effect'),
                                policy_resource=statement.get('Resource')
                            )

                            policy_principal = statement.get('Principal')
                            if policy_principal and isinstance(policy_principal, dict):
                                for k, v in policy_principal.items():
                                    principal_type = k or ''
                                    principal_name = v or ''

                                    principal = AWSIAMPolicyPrincipal(
                                        principal_type=principal_type,
                                        principal_name=principal_name
                                    )
                                    permission.policy_principals = [principal]
                                    permissions.append(permission)

                                    policy = AWSIAMPolicy(
                                        policy_permissions=permissions,
                                        policy_version=version
                                    )
                                    device.es_access_policies.append(policy)
                            else:
                                if policy_principal is not None:
                                    logger.warning(f'Malformed policy principal.'
                                                   f' Expected a dict, got '
                                                   f'{type(policy_principal)}: '
                                                   f'{str(policy_principal)}')
                        else:
                            if statement is not None:
                                logger.warning(f'Malformed policy statement. '
                                               f'Expected a dict, got '
                                               f'{type(statement)}: '
                                               f'{str(statement)}')

        new_snapshot_options = list()
        snapshot_options = domain.get('SnapshotOptions')
        if snapshot_options and isinstance(snapshot_options, dict):
            # there could be a random and large number of these
            for option, value in snapshot_options.items():
                snapshot_option = AWSElasticsearchSnapshotOption(
                    option=option,
                    value=str(value)  # could be an int or a str
                )
                new_snapshot_options.append(snapshot_option)

            device.es_snapshot_options = new_snapshot_options
        else:
            if snapshot_options is not None:
                logger.warning(f'Malformed Elasticsearch snapshot options. '
                               f'Expected a dict, got {type(snapshot_options)}:'
                               f' {str(snapshot_options)}')

        vpc_options = domain.get('VPCOptions')
        if vpc_options and isinstance(vpc_options, dict):
            subnet_ids = list()
            availability_zones = list()
            secgroup_ids = list()

            device.vpc_id = vpc_options.get('VPCId')

            new_vpc_options = AWSElasticsearchVPCOptions()

            subnets = vpc_options.get('SubnetIds')
            if subnets and isinstance(subnets, list):
                for subnet_id in subnets:
                    if subnet_id and isinstance(subnet_id, str):
                        subnet_ids.append(subnet_id)
                    else:
                        if subnet_id is not None:
                            logger.warning(f'Malformed subnet ID. Expected a '
                                           f'str, got {type(subnet_id)}: '
                                           f'{str(subnet_id)}')

                new_vpc_options.subnet_ids = subnet_ids
            else:
                if subnets is not None:
                    logger.warning(f'Malformed Elasticsearch subnets. '
                                   f'Expected a list, got {type(subnets)}: '
                                   f'{str(subnets)}')

            azs = vpc_options.get('AvailabilityZones')
            if azs and isinstance(azs, list):
                for az in azs:
                    if az and isinstance(az, str):
                        availability_zones.append(az)
                    else:
                        if az is not None:
                            logger.warning(f'Malformed availability zone. '
                                           f'Expected a str, got '
                                           f'{type(az)}: {str(az)}')

                new_vpc_options.availability_zones = availability_zones
            else:
                if subnets is not None:
                    logger.warning(f'Malformed Elasticsearch availability '
                                   f'zones. Expected a list, got '
                                   f'{type(subnets)}: {str(subnets)}')

            security_groups = vpc_options.get('SecurityGroupIds')
            if security_groups and isinstance(security_groups, list):
                for security_group in security_groups:
                    if security_group and isinstance(security_group, str):
                        secgroup_ids.append(security_group)
                    else:
                        if security_group is not None:
                            logger.warning(f'Malformed security group ID. '
                                           f'Expected a str, got '
                                           f'{type(security_group)}: '
                                           f'{str(security_group)}')

                new_vpc_options.security_group_ids = secgroup_ids
            else:
                if security_groups is not None:
                    logger.warning(f'Malformed Elasticsearch security groups. '
                                   f'Expected a list, got '
                                   f'{type(security_groups)}: '
                                   f'{str(security_groups)}')

            device.es_vpc_options = new_vpc_options
        else:
            device.es_configured_as_public = True
            if vpc_options is not None:
                logger.warning(f'Malformed Elasticsearch VPC options. Expected '
                               f'a dict, got {type(vpc_options)}:'
                               f'{str(vpc_options)}')

        cognito_options = domain.get('CognitoOptions')
        if cognito_options and isinstance(cognito_options, dict):
            new_cognito_options = AWSElasticsearchCognitoOption(
                enabled=cognito_options.get('Enabled'),
                user_pool_id=cognito_options.get('UserPoolId'),
                identity_pool_id=cognito_options.get('IdentityPoolId'),
                role_arn=cognito_options.get('RoleArn')
            )
            device.es_cognito_options = new_cognito_options
        else:
            if cognito_options is not None:
                logger.warning(f'Malformed Elasticsearch cognito options. '
                               f'Expected a dict, got {type(cognito_options)}: '
                               f'{str(cognito_options)}')

        encryption_options = domain.get('EncryptionAtRestOptions')
        if encryption_options and isinstance(encryption_options, dict):
            new_encryption_options = AWSElasticsearchEncryptionOption(
                enabled=encryption_options.get('Enabled'),
                kms_key_id=encryption_options.get('KmsKeyId')
            )
            device.es_encryption_options = new_encryption_options
        else:
            if encryption_options is not None:
                logger.warning(f'Malformed Elasticsearch encryption options. '
                               f'Expected a dict, got '
                               f'{type(encryption_options)}: '
                               f'{str(encryption_options)}')

        node_encryption_option = domain.get('NodeToNodeEncryptionOptions')
        if node_encryption_option and isinstance(node_encryption_option, dict):
            enabled = node_encryption_option.get('Enabled')
            if enabled and isinstance(enabled, bool):
                device.es_node_to_node_encryption_option = enabled

        new_advanced_options = list()
        advanced_options = domain.get('AdvancedOptions')
        if advanced_options and isinstance(advanced_options, dict):
            # there could be a random and large number of these
            for option, value in advanced_options.items():
                advanced_option = AWSElasticsearchAdvancedOption(
                    option=option,
                    value=value
                )
                new_advanced_options.append(advanced_option)

            device.es_advanced_options = new_advanced_options
        else:
            if advanced_options is not None:
                logger.warning(f'Malformed Elasticsearch advanced options. '
                               f'Expected a dict, got {type(advanced_options)}:'
                               f' {str(advanced_options)}')

        log_publishing_options = domain.get('LogPublishingOptions')
        if log_publishing_options and isinstance(log_publishing_options, dict):
            for option_key, option_value_dict in log_publishing_options.items():
                if isinstance(option_key, str) and isinstance(option_value_dict, dict):
                    new_log_options = AWSElasticsearchLogOptions(
                        log_type=option_key,
                        cloudwatch_logs_arn=option_value_dict.get('CloudWatchLogsLogGroupArn'),
                        enabled=option_value_dict.get('Enabled')
                    )
                    device.es_log_publishing_options = new_log_options
                else:
                    if option_key is not None or option_value_dict is not None:
                        logger.warning(f'Malformed Elasticsearch log publishing'
                                       f' option. {str(log_publishing_options)}')
        else:
            if log_publishing_options is not None:
                logger.warning(f'Malformed Elasticsearch log publishing '
                               f'options. Expected a dict, got '
                               f'{type(log_publishing_options)}: '
                               f'{str(log_publishing_options)}')

        software_options = domain.get('ServiceSoftwareOptions')
        if software_options and isinstance(software_options, dict):
            new_software_option = AWSElasticsearchServiceSoftwareOption(
                current_version=software_options.get('CurrentVersion'),
                new_version=software_options.get('NewVersion'),
                update_available=software_options.get('UpdateAvailable'),
                cancellable=software_options.get('Cancellable'),
                update_status=software_options.get('UpdateStatus'),
                description=software_options.get('Description'),
                automated_update_date=parse_date(software_options.get('AutomatedUpdateDate')),
                optional_deployment=software_options.get('OptionalDeployment')
            )
            device.es_service_software_options = new_software_option
        else:
            if software_options is not None:
                logger.warning(f'Malformed Elasticsearch service software '
                               f'options. Expected a dict, got '
                               f'{type(software_options)}: '
                               f'{str(software_options)}')

        endpoint_options = domain.get('DomainEndpointOptions')
        if endpoint_options and isinstance(endpoint_options, dict):
            new_endpoint_options = AWSElasticsearchEndpointOption(
                enforce_https=endpoint_options.get('EnforceHTTPS'),
                tls_policy=endpoint_options.get('TLSSecurityPolicy')
            )
            device.es_domain_endpoint_options = new_endpoint_options
        else:
            if endpoint_options is not None:
                logger.warning(f'Malformed Elasticsearch endpoint options. '
                               f'Expected a dict, got {type(endpoint_options)}: '
                               f'{str(endpoint_options)}')

        security_options = domain.get('AdvancedSecurityOptions')
        if security_options and isinstance(security_options, dict):
            new_security_options = AWSElasticsearchSecurityOption(
                enabled=security_options.get('Enabled'),
                internal_user_db_enabled=security_options.get('InternalUserDatabaseEnabled')
            )
            device.es_advanced_security_options = new_security_options
        else:
            if security_options is not None:
                logger.warning(f'Malformed Elasticsearch endpoint options. '
                               f'Expected a dict, got {type(security_options)}:'
                               f' {str(security_options)}')

        device.set_raw(domain)
        logger.debug(f'Finished parsing Elasticsearch domain: '
                     f'{domain.get("DomainName")}')
        return device
    except Exception:
        logger.exception(f'Unable to parse Elasticsearch domain: '
                         f'{str(domain)}')


def check_security_groups(client_data: dict, resource: dict) -> bool:
    """
    This is a brute force check to see if the security group(s) attached
    to a device have '0.0.0.0/0', '::' or '0:0:0:0:0:0:0:0' as ingress
    allowances. If any of these cases is found, we will return the
    is_public as True.

    :param client_data: client connections
    :param resource: elasticsearch domain information
    :return is_public: a value that specifies if the security group may
    publicly expose a resource.
    """
    is_public = False
    vpc_options = resource.get('VPCOptions')
    if isinstance(vpc_options, dict):
        security_groups = vpc_options.get('SecurityGroupIds')
        if isinstance(security_groups, list):
            ec2_client = client_data.get('ec2')
            security_groups_raw = ec2_client.describe_security_groups(GroupIds=security_groups)
            if isinstance(security_groups_raw, dict):
                sgs_raw = security_groups_raw.get('SecurityGroups')
                if isinstance(sgs_raw, list):
                    for security_group in sgs_raw:
                        ip_permissions = security_group.get('IpPermissions')
                        if isinstance(ip_permissions, list):
                            for ip_permission in ip_permissions:
                                ip_ranges = ip_permission.get('IpRanges')
                                if isinstance(ip_ranges, list):
                                    for ip_range in ip_ranges:
                                        if isinstance(ip_range, dict):
                                            if ip_range.get('CidrIp') == '0.0.0.0/0':
                                                is_public = True
                                                break
                                        else:
                                            logger.warning(
                                                f'Malformed IP range. '
                                                f'Expected a dict, '
                                                f'got {type(ip_range)}: '
                                                f'{str(ip_range)}')
                                else:
                                    logger.warning(
                                        f'Malformed IP ranges. Expected a list, '
                                        f'got {type(ip_ranges)}: {str(ip_ranges)}')

                                ipv6_ranges = ip_permission.get('Ipv6Ranges')
                                if isinstance(ipv6_ranges, list):
                                    for ipv6_range in ipv6_ranges:
                                        if isinstance(ipv6_range, dict):
                                            if ipv6_range.get('CidrIpv6') in ['0:0:0:0:0:0:0:0', '::']:
                                                is_public = True
                                                break
                                else:
                                    logger.warning(
                                        f'Malformed IPv6 ranges. Expected a '
                                        f'list, got {type(ipv6_ranges)}: '
                                        f'{str(ipv6_ranges)}')
                        else:
                            logger.warning(
                                f'Malformed IP permissions. Expected a list, '
                                f'got {type(ip_permissions)}: '
                                f'{str(ip_permissions)}')
                else:
                    logger.warning(
                        f'Malformed raw security group data. Expected a list, '
                        f'got {type(sgs_raw)}: {str(sgs_raw)}')
    else:
        if vpc_options is not None:
            logger.warning(f'Malformed VPC options. Expected a dict, got '
                           f'{type(vpc_options)}: {str(vpc_options)}')
    return is_public
