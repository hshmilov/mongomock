import logging
from typing import Optional

from aws_adapter.connection.structures import AWSDeviceAdapter, RDSInfo, RDSDBParameterGroup, RDSDBSecurityGroup, \
    RDSVPCSecurityGroup, RDSSubnet, RDSDomainMembership
from aws_adapter.connection.utils import get_paginated_marker_api, make_ip_rules_list, add_generic_firewall_rules
from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements, too-many-locals
def query_devices_by_client_by_source_rds(client_data: dict):
    if client_data.get('rds') is not None:
        try:
            rds_client = client_data.get('rds')
            for rds_page in get_paginated_marker_api(rds_client.describe_db_instances):
                yield from (rds_page.get('DBInstances') or [])

        except Exception:
            logger.exception(f'Problem fetching information about RDS')


def parse_raw_data_inner_rds(
        device: AWSDeviceAdapter,
        rds_instance_raw: dict,
        generic_resources: dict
) -> Optional[AWSDeviceAdapter]:
    # Parse RDS's
    vpcs_by_id = generic_resources.get('vpcs') or {}
    security_group_dict = generic_resources.get('security_groups') or {}
    try:
        device.id = rds_instance_raw['DBInstanceArn']
        device.name = rds_instance_raw['DBInstanceIdentifier']
        device.aws_device_type = 'RDS'
        device.cloud_id = rds_instance_raw['DBInstanceArn']
        device.cloud_provider = 'AWS'
        device.aws_availability_zone = rds_instance_raw.get('AvailabilityZone')

        rds_data = RDSInfo()
        if isinstance(rds_instance_raw.get('AllocatedStorage'), int):
            rds_data.allocated_storage = rds_instance_raw.get('AllocatedStorage')

        rds_data.auto_minor_version_upgrade = rds_instance_raw.get('AutoMinorVersionUpgrade')
        rds_data.backup_retention_period = rds_instance_raw.get('BackupRetentionPeriod')
        rds_data.ca_certificate_identifier = rds_instance_raw.get('CACertificateIdentifier')
        rds_data.copy_tags_to_snapshot = rds_instance_raw.get('CopyTagsToSnapshot')
        rds_data.db_instance_arn = rds_instance_raw.get('DBInstanceArn')
        rds_data.db_instance_class = rds_instance_raw.get('DBInstanceClass')
        rds_data.db_instance_status = rds_instance_raw.get('DBInstanceStatus')
        rds_data.db_name = rds_instance_raw.get('DBName')
        rds_data.db_instance_port = rds_instance_raw.get('DbInstancePort')
        rds_data.dbi_resource_id = rds_instance_raw.get('DbiResourceId')
        rds_data.deletion_protection = rds_instance_raw.get('DeletionProtection')
        rds_data.engine = rds_instance_raw.get('Engine')
        rds_data.engine_version = rds_instance_raw.get('EngineVersion')
        rds_data.iam_database_authentication_enabled = rds_instance_raw.get(
            'IAMDatabaseAuthenticationEnabled')
        rds_data.instance_create_time = parse_date(rds_instance_raw.get('InstanceCreateTime'))
        rds_data.latest_restorable_time = parse_date(rds_instance_raw.get('LatestRestorableTime'))
        rds_data.license_model = rds_instance_raw.get('LicenseModel')
        rds_data.master_username = rds_instance_raw.get('MasterUsername')
        rds_data.monitoring_interval = rds_instance_raw.get('MonitoringInterval')
        rds_data.mutli_az = rds_instance_raw.get('MultiAZ')
        rds_data.performance_insights_enabled = rds_instance_raw.get('PerformanceInsightsEnabled')
        rds_data.preferred_backup_window = rds_instance_raw.get('PreferredBackupWindow')
        rds_data.preferred_maintenance_window = rds_instance_raw.get('PreferredMaintenanceWindow')
        rds_data.publicly_accessible = rds_instance_raw.get('PubliclyAccessible')
        rds_data.storage_encrypted = rds_instance_raw.get('StorageEncrypted')
        rds_data.storage_type = rds_instance_raw.get('StorageType')

        for parameter_group in (rds_instance_raw.get('DBParameterGroups') or []):
            try:
                rds_data.rds_db_parameter_group.append(
                    RDSDBParameterGroup(
                        db_parameter_group_name=parameter_group.get('DBParameterGroupName'),
                        db_parameter_apply_status=parameter_group.get('ParameterApplyStatus')
                    )
                )
            except Exception:
                logger.exception(f'Failed adding db parameter group')

        all_security_groups = set()
        for db_security_group in (rds_instance_raw.get('DBSecurityGroups') or []):
            try:
                db_security_group_name = db_security_group.get('DBSecurityGroupName')
                db_security_group_status = db_security_group.get('Status')
                rds_data.rds_db_security_group.append(
                    RDSDBSecurityGroup(
                        db_security_group_name=db_security_group_name,
                        status=db_security_group_status
                    )
                )
                if str(db_security_group_status).lower() == 'active':
                    all_security_groups.add(db_security_group_name)
            except Exception:
                logger.exception(f'Failed adding db security group')
        for vpc_security_group in (rds_instance_raw.get('VpcSecurityGroups') or []):
            try:
                vpc_security_group_id = vpc_security_group.get('VpcSecurityGroupId')
                vpc_security_group_status = vpc_security_group.get('Status')
                if not vpc_security_group_id:
                    continue

                if vpc_security_group_status and str(vpc_security_group_status).lower() == 'active':
                    all_security_groups.add(vpc_security_group_id)
                rds_data.vpc_security_groups.append(
                    RDSVPCSecurityGroup(
                        vpc_security_group_id=vpc_security_group_id,
                        status=vpc_security_group_status
                    )
                )
            except Exception:
                logger.exception(f'Failed adding vpc security group')

        try:
            for security_group in all_security_groups:
                security_group_raw = security_group_dict.get(security_group)
                if security_group_raw and isinstance(security_group_raw, dict):
                    try:
                        outbound_rules = make_ip_rules_list(
                            security_group_raw.get('IpPermissionsEgress'))
                    except Exception:
                        # That's probably a classic security group
                        outbound_rules = None
                    inbound_rules = make_ip_rules_list(security_group_raw.get('IpPermissions'))
                    device.add_aws_security_group(name=security_group_raw.get('GroupName'),
                                                  outbound=outbound_rules,
                                                  inbound=inbound_rules)

                    try:
                        all_rules_lists = [(outbound_rules, 'EGRESS'), (inbound_rules, 'INGRESS')]
                        for rule_list, direction in all_rules_lists:
                            try:
                                if not rule_list:
                                    continue
                                add_generic_firewall_rules(
                                    device,
                                    security_group_raw.get('GroupName'),
                                    'AWS RDS Security Group',
                                    direction,
                                    rule_list
                                )
                            except Exception:
                                logger.exception(f'Error adding generic firewall rules')
                    except Exception:
                        logger.exception(f'Could not add generic firewall rules')
                else:
                    if security_group_raw:
                        device.add_aws_security_group(name=security_group_raw.get('GroupName'))
        except Exception:
            logger.exception(f'Problem parsing RDS security group')

        subnet_group = rds_instance_raw.get('DBSubnetGroup') or {}
        rds_data.db_subnet_group_name = subnet_group.get('DBSubnetGroupName')
        rds_data.db_subnet_group_description = subnet_group.get('DBSubnetGroupDescription')
        rds_data.db_subnet_group_status = subnet_group.get('SubnetGroupStatus')

        try:
            for subnet_raw in (subnet_group.get('Subnets') or []):
                rds_data.db_subnets.append(RDSSubnet(
                    subnet_az=(subnet_raw.get('SubnetAvailabilityZone') or {}).get('Name'),
                    subnet_id=subnet_raw.get('SubnetIdentifier'),
                    subnet_status=subnet_raw.get('SubnetStatus')
                ))
        except Exception:
            logger.exception(f'Failed adding RDS subnets')

        try:
            for domain_membership_raw in (rds_instance_raw.get('DomainMemberships') or []):
                rds_data.domain_memberships.append(RDSDomainMembership(
                    domain=domain_membership_raw.get('Domain'),
                    status=domain_membership_raw.get('Status'),
                    fqdn=domain_membership_raw.get('FQDN'),
                    iam_role_name=domain_membership_raw.get('IAMRoleName')
                ))
        except Exception:
            logger.exception(f'Failed adding domain membership')

        endpoint_data = rds_instance_raw.get('Endpoint') or {}
        rds_data.endpoint_address = endpoint_data.get('Address')
        rds_data.endpoint_hosted_zone_id = endpoint_data.get('HostedZoneId')
        rds_data.endpoint_port = endpoint_data.get('Port')

        # To be added - parse db security groups, use `describe_db_security_groups`

        device.vpc_id = subnet_group.get('VpcId')
        device.vpc_name = (vpcs_by_id.get(subnet_group.get('VpcId')) or {}).get('Name')
        try:
            for vpc_tag_key, vpc_tag_value in (vpcs_by_id.get(subnet_group.get('VpcId')) or {}).items():
                device.add_aws_vpc_tag(key=vpc_tag_key, value=vpc_tag_value)
        except Exception:
            logger.exception(f'Could not parse aws vpc tags')
        device.rds_data = rds_data

        device.set_raw(rds_instance_raw)
        return device
    except Exception:
        logger.exception(f'Could not parse RDS device {rds_instance_raw}')
