import datetime

from axonius.devices.device_or_container_adapter import DeviceOrContainerAdapter
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.utils.parsing import format_ip


class AWSTagKeyValue(SmartJsonClass):
    """ A definition for a key value field"""
    key = Field(str, 'AWS Tag Key')
    value = Field(str, 'AWS Tag Value')


class AWSIAMPolicy(SmartJsonClass):
    policy_name = Field(str, 'Policy Name')
    policy_type = Field(str, 'Policy Type', enum=['Managed', 'Inline', 'Group Managed'])


class AWSIAMAccessKey(SmartJsonClass):
    access_key_id = Field(str, 'ID')
    status = Field(str, 'Status', enum=['Active', 'Inactive'])
    create_date = Field(datetime.datetime, 'Creation Date')
    last_used_time = Field(datetime.datetime, 'Last Used Time')
    last_used_service = Field(str, 'Last Used Service Name')
    last_used_region = Field(str, 'Last Used Region')


class AWSIPRule(SmartJsonClass):
    from_port = Field(int, 'From Port')
    to_port = Field(int, 'To Port')
    ip_protocol = Field(str, 'IP Protocol')
    ip_ranges = ListField(str, 'CIDR')


class AWSSecurityGroup(SmartJsonClass):
    name = Field(str, 'Security Group Name')
    inbound = ListField(AWSIPRule, 'Inbound Rules')
    outbound = ListField(AWSIPRule, 'Outbound Rules')


class AWSRole(SmartJsonClass):
    role_name = Field(str, 'Name')
    role_arn = Field(str, 'ARN')
    role_id = Field(str, 'ID')
    role_description = Field(str, 'Description')
    role_permissions_boundary_policy_name = Field(str, 'Permissions Boundary Policy')
    role_attached_policies_named = ListField(str, 'Attached Policies')


class AWSEBSVolumeAttachment(SmartJsonClass):
    attach_time = Field(datetime.datetime, 'Attach Time')
    device = Field(str, 'Device')
    state = Field(str, 'State')
    delete_on_termination = Field(bool, 'Delete On Termination')


class AWSEBSVolume(SmartJsonClass):
    attachments = ListField(AWSEBSVolumeAttachment, 'Attachments')
    name = Field(str, 'Name')
    availability_zone = Field(str, 'Availability Zone')
    create_time = Field(datetime.datetime, 'Create Time')
    encrypted = Field(bool, 'Encrypted')
    kms_key_id = Field(str, 'Kms Key ID')
    size = Field(str, 'Size (GB)')
    snapshot_id = Field(str, 'Snapshot ID')
    state = Field(str, 'State')
    volume_id = Field(str, 'Volume ID')
    iops = Field(int, 'Iops')
    tags = ListField(AWSTagKeyValue, 'Tags')
    volume_type = Field(str, 'Volume Type')


class AWSLoadBalancer(SmartJsonClass):
    name = Field(str, 'Name')
    dns = Field(str, 'DNS')
    scheme = Field(str, 'Scheme', enum=['internet-facing', 'internal'])
    type = Field(str, 'Type', enum=['classic', 'network', 'application'])
    subnets = ListField(str, 'Subnets')
    lb_protocol = Field(str, 'LB Protocol')
    instance_protocol = Field(str, 'Instance Protocol')
    lb_port = Field(int, 'LB Port')
    instance_port = Field(int, 'Instance Port')
    ips = ListField(str, 'External IPs', converter=format_ip, json_format=JsonStringFormat.ip)
    last_ip_by_dns_query = Field(str, 'Last IP by DNS Query', converter=format_ip, json_format=JsonStringFormat.ip)


class SSMComplianceSummary(SmartJsonClass):
    status = Field(str, 'Status')
    overall_severity = Field(str, 'Overall Severity')
    last_execution = Field(datetime.datetime, 'Last Execution Time')

    compliant_count = Field(int, 'Compliant Count')
    compliant_critical_count = Field(int, 'Compliant Critical Count')
    compliant_high_count = Field(int, 'Compliant High Count')
    compliant_medium_count = Field(int, 'Compliant Medium Count')
    compliant_low_count = Field(int, 'Compliant Low Count')
    compliant_informational_count = Field(int, 'Compliant Informational Count')
    compliant_unspecified_count = Field(int, 'Compliant Unspecified Count')

    non_compliant_count = Field(int, 'Non Compliant Count')
    non_compliant_critical_count = Field(int, 'Non Compliant Critical Count')
    non_compliant_high_count = Field(int, 'Non Compliant High Count')
    non_compliant_medium_count = Field(int, 'Non Compliant Medium Count')
    non_compliant_low_count = Field(int, 'Non Compliant Low Count')
    non_compliant_informational_count = Field(int, 'Non Compliant Informational Count')
    non_compliant_unspecified_count = Field(int, 'Non Compliant Unspecified Count')


class SSMInfo(SmartJsonClass):
    ping_status = Field(str, 'Ping Status')
    last_ping_date = Field(datetime.datetime, 'Last Ping Date')
    agent_version = Field(str, 'Agent Version')
    is_latest_version = Field(bool, 'Is Latest Version')
    activation_id = Field(str, 'Activation Id')
    registration_date = Field(datetime.datetime, 'Registration Date')
    association_status = Field(str, 'Association Status')
    last_association_execution_date = Field(datetime.datetime, 'Last Association Execution Date')
    last_successful_association_execution_date = Field(datetime.datetime, 'Last Successful Association Execution Date')
    patch_group = Field(str, 'Patch Group')
    baseline_id = Field(str, 'Patch Baseline Id')
    baseline_name = Field(str, 'Patch Baseline Name')
    baseline_description = Field(str, 'Patch Baseline Description')
    patch_compliance_summaries = ListField(SSMComplianceSummary, 'Patch Compliance')
    association_compliance_summaries = ListField(SSMComplianceSummary, 'Association Compliance')
    last_seen = Field(datetime.datetime, 'Last Seen')


class RDSDBParameterGroup(SmartJsonClass):
    db_parameter_group_name = Field(str, 'DB Parameter Group Name')
    db_parameter_apply_status = Field(str, 'DB Parameter Apply Status')


class RDSDBSecurityGroup(SmartJsonClass):
    db_security_group_name = Field(str, 'DB Security Group Name')
    status = Field(str, 'Status')


class RDSVPCSecurityGroup(SmartJsonClass):
    vpc_security_group_id = Field(str, 'Security Group ID')
    status = Field(str, 'Status')


class RDSSubnet(SmartJsonClass):
    subnet_az = Field(str, 'Availability Zone')
    subnet_id = Field(str, 'ID')
    subnet_status = Field(str, 'Status')


class RDSDomainMembership(SmartJsonClass):
    domain = Field(str, 'Domain')
    status = Field(str, 'Status')
    fqdn = Field(str, 'FQDN')
    iam_role_name = Field(str, 'IAM Role Name')


class RDSInfo(SmartJsonClass):
    allocated_storage = Field(int, 'Allocated Storage')
    auto_minor_version_upgrade = Field(bool, 'Auto Minor Version Upgrade')
    backup_retention_period = Field(int, 'Backup Retention Period')
    ca_certificate_identifier = Field(str, 'CA Certificate Identifier')
    copy_tags_to_snapshot = Field(bool, 'Copy Tags To Snapshot')
    db_instance_arn = Field(str, 'DB Instance ARN')
    db_instance_class = Field(str, 'DB Instance Class')
    db_instance_status = Field(str, 'DB Instance Status')
    db_name = Field(str, 'Initial Database Name')
    db_instance_port = Field(int, 'DB Instance Port')
    dbi_resource_id = Field(str, 'DBI Resource ID')
    deletion_protection = Field(bool, 'Deletion Protection')
    engine = Field(str, 'Engine')
    engine_version = Field(str, 'Engine Version')
    iam_database_authentication_enabled = Field(bool, 'IAM Database Authentication Enabled')
    instance_create_time = Field(datetime.datetime, 'Instance Create Time')
    latest_restorable_time = Field(datetime.datetime, 'Latest Restorable Time')
    license_model = Field(str, 'License Model')
    master_username = Field(str, 'Master Username')
    monitoring_interval = Field(int, 'Monitoring Interval')
    mutli_az = Field(bool, 'Multi AZ')
    performance_insights_enabled = Field(bool, 'Performance Insights Enabled')
    preferred_backup_window = Field(str, 'Preferred Backup Window')
    preferred_maintenance_window = Field(str, 'Preferred Maintenance Window')
    publicly_accessible = Field(bool, 'Publicly Accessible')
    storage_encrypted = Field(bool, 'Storage Encrypted')
    storage_type = Field(str, 'Storage Type')

    rds_db_parameter_group = ListField(RDSDBParameterGroup, 'DB Parameter Group')
    rds_db_security_group = ListField(RDSDBSecurityGroup, 'DB Security Group')
    vpc_security_groups = ListField(RDSVPCSecurityGroup, 'VPC Security Groups')

    db_subnet_group_name = Field(str, 'Subnet Group Name')
    db_subnet_group_description = Field(str, 'Subnet Group Description')
    db_subnet_group_status = Field(str, 'Subnet Group Status')
    db_subnets = ListField(RDSSubnet, 'Subnets')

    domain_memberships = ListField(RDSDomainMembership, 'Domain Membership')

    endpoint_address = Field(str, 'Endpoint Address')
    endpoint_hosted_zone_id = Field(str, 'Endpoint Hosted Zone ID')
    endpoint_port = Field(int, 'Endpoint Port')


class AWSS3BucketACL(SmartJsonClass):
    grantee_display_name = Field(str, 'Grantee Display Name')
    grantee_email_address = Field(str, 'Grantee Email Address')
    grantee_id = Field(str, 'Grantee ID')
    grantee_type = Field(str, 'Grantee Type')
    grantee_uri = Field(str, 'Grantee URI')
    grantee_permission = Field(str, 'Grantee Permission')


class AWSS3PolicyStatement(SmartJsonClass):
    action = ListField(str, 'Action')
    effect = Field(str, 'Effect')
    principal = Field(str, 'Principal')
    resource = Field(str, 'Resource')
    sid = Field(str, 'Sid')
    condition = Field(str, 'Condition')


class AWSS3BucketPolicy(SmartJsonClass):
    bucket_policy = Field(str, 'Contents (Json)')
    bucket_policy_id = Field(str, 'ID')
    statements = ListField(AWSS3PolicyStatement, 'Statements')


class AWSMFADevice(SmartJsonClass):
    serial_number = Field(str, 'Serial Number')
    enable_date = Field(datetime.datetime, 'Enable Date')


class AWSWorkspaceDevice(SmartJsonClass):
    workspace_id = Field(str, 'ID')
    directory_id = Field(str, 'Directory ID')
    directory_alias = Field(str, 'Directory Alias')
    directory_name = Field(str, 'Directory Name')

    username = Field(str, 'Username')
    state = Field(str, 'State')
    bundle_id = Field(str, 'Bundle ID')
    error_message = Field(str, 'Error Message')
    error_code = Field(str, 'Error Code')
    volume_encryption_key = Field(str, 'Volume Encryption Key')
    running_mode = Field(str, 'Running Mode')
    running_mode_auto_stop_timeout_in_minutes = Field(int, 'Running Mode Auto Stop Timeout In Minutes')
    user_volume_size_gib = Field(int, 'User Volume Size (GiB)')
    root_volume_size_gib = Field(int, 'Root Volume Size (GiB)')
    user_volume_encryption_enabled = Field(bool, 'User Volume Encryption Enabled')
    root_volume_encryption_enabled = Field(bool, 'Root Volume Encryption Enabled')
    compute_type_name = Field(str, 'Compute Type Name')
    connection_state = Field(str, 'Connection State')
    connection_state_check_timestamp = Field(datetime.datetime, 'Connection State Check Timestamp')
    last_known_user_connection_timestamp = Field(datetime.datetime, 'Last Known User Connection Timestamp')


class AWSLambdaPolicy(SmartJsonClass):
    raw = Field(str, 'Contents (Json)')
    statements = ListField(AWSS3PolicyStatement, 'Statements')


class AWSLambda(SmartJsonClass):
    name = Field(str, 'Function Name')
    arn = Field(str, 'Function Arn')
    runtime = Field(str, 'Runtime')
    role = Field(str, 'Role')
    handler = Field(str, 'Handler')
    code_size = Field(int, 'Code Size')
    description = Field(str, 'Description')
    timeout = Field(int, 'Timeout')
    memory_size = Field(int, 'Memory Size')
    last_modified = Field(datetime.datetime, 'Last Modified')
    code_sha_256 = Field(str, 'CodeSha256')
    version = Field(str, 'Version')
    subnets = ListField(str, 'Subnet Ids')
    security_groups = ListField(str, 'Security Group Ids')
    vpc_id = Field(str, 'VPC ID')
    kms_key_arn = Field(str, 'KMS Key Arn')
    tracing_config_mode = Field(str, 'Tracing Config Mode')
    master_arn = Field(str, 'Master Arn')
    revision_id = Field(str, 'Revision Id')
    layers = ListField(str, 'Layer Arn')
    policy = Field(AWSLambdaPolicy, 'Policy')


class AWSRoute53Record(SmartJsonClass):
    resource_type = Field(str, 'Resource Type')
    ttl = Field(int, 'TTL')
    set_identifier = Field(str, 'Set Identifier')
    weight = Field(int, 'Weight')
    region = Field(str, 'Region')
    geo_location_continent_code = Field(str, 'GeoLocation Continent Code')
    geo_location_country_code = Field(str, 'GeoLocation Country Code')
    geo_location_subdivision_code = Field(str, 'GeoLocation Subdivision Code')
    failover = Field(str, 'Failover')
    multi_value_answer = Field(bool, 'Multi Value Answer')
    health_check_id = Field(str, 'Health Check Id')
    traffic_policy_instance_id = Field(str, 'Traffic Policy Instance Id')
    resource_records = ListField(str, 'Resource Records')
    alias_target_hosted_zone_id = Field(str, 'Alias Target Hosted Zone Id')
    alias_target_dns_name = Field(str, 'Alias Target DNS Name')
    alias_target_evaluate_target_health = Field(bool, 'Alias Target Evaluate Target Health')


class AWSAdapter:
    account_tag = Field(str, 'Account Tag')
    aws_account_alias = ListField(str, 'Account Alias')
    aws_account_id = Field(int, 'Account ID')
    aws_region = Field(str, 'Region')
    aws_source = Field(str, 'Source')  # Specify if it is from a user, a role, or what.
    aws_tags = ListField(AWSTagKeyValue, 'AWS Tags')


class AWSUserAdapter(UserAdapter, AWSAdapter):
    user_path = Field(str, 'User Path')
    user_arn = Field(str, 'User Arn')
    user_create_date = Field(datetime.datetime, 'User Create Date')
    user_pass_last_used = Field(datetime.datetime, 'User Password Last Used')
    user_permission_boundary_arn = Field(str, 'User Permission Boundary Arn')

    user_attached_policies = ListField(AWSIAMPolicy, 'Policies')
    user_attached_keys = ListField(AWSIAMAccessKey, 'Access Keys')

    user_associated_mfa_devices = ListField(AWSMFADevice, 'Associated MFA Devices')
    user_is_password_enabled = Field(bool, 'User Is Password Enabled')


class AWSDeviceAdapter(DeviceOrContainerAdapter, AWSAdapter):
    ssm_data_last_seen = Field(datetime.datetime)
    aws_availability_zone = Field(str, 'Availability Zone')
    aws_device_type = Field(
        str,
        'Device Type (EC2 / ECS / EKS / ELB / Managed / NAT / RDS / S3 / Workspace / Lambda / Route53)',
        enum=['EC2', 'ECS', 'EKS', 'ELB', 'Managed', 'NAT', 'RDS', 'S3', 'Workspace', 'Lambda', 'Route53']
    )
    security_groups = ListField(AWSSecurityGroup, 'Security Groups')

    # EC2-specific fields
    instance_type = Field(str, 'Instance Type')
    key_name = Field(str, 'Key Name')
    private_dns_name = Field(str, 'Private Dns Name')
    monitoring_state = Field(str, 'Monitoring State')
    launch_time = Field(datetime.datetime, 'Launch Time')
    image_id = Field(str, 'AMI (Image) ID')
    aws_attached_role = Field(AWSRole, 'Attached Role')
    aws_load_balancers = ListField(AWSLoadBalancer, 'Load Balancer (ELB)')
    ebs_volumes = ListField(AWSEBSVolume, 'EBS Volumes')

    # VPC Generic Fields
    subnet_id = Field(str, 'Subnet Id')
    subnet_name = Field(str, 'Subnet Name')
    vpc_id = Field(str, 'VPC Id')
    vpc_name = Field(str, 'VPC Name')

    # ECS / EKS specific fields
    container_instance_arn = Field(str, 'Task ContainerInstance ID/ARN')
    ecs_device_type = Field(str, 'ECS Launch Type', enum=['Fargate', 'EC2'])
    ecs_ec2_instance_id = Field(str, 'ECS EC2 Instance ID')

    # SSM specific fields
    ssm_data = Field(SSMInfo, 'SSM Information')

    # RDS specific fields
    rds_data = Field(RDSInfo, 'RDS Information')

    # Workspace specific fields
    workspace_data = Field(AWSWorkspaceDevice, 'Workspace Information')

    # Lambda specific fields
    lambda_data = Field(AWSLambda, 'Lambda Information')

    # Route53 specific fields
    route53_zone_id = Field(str, 'Route53 Zone ID')
    route53_zone_name = Field(str, 'Route53 Zone Name')
    route53_zone_is_private = Field(bool, 'Route53 Zone is Private')
    route53_data = ListField(AWSRoute53Record, 'Route53 Record')
    dns_names = ListField(str, 'Associated DNS')

    # S3 specific fields
    s3_bucket_name = Field(str, 'S3 Bucket Name')
    s3_creation_date = Field(str, 'S3 Bucket Creation Date')
    s3_owner_name = Field(str, 'S3 Owner Display Name')
    s3_owner_id = Field(str, 'S3 Owner ID')
    s3_bucket_is_public = Field(bool, 'S3 Bucket Public')
    s3_bucket_location = Field(str, 'S3 Bucket Location')
    s3_bucket_acls = ListField(AWSS3BucketACL, 'S3 ACL')
    s3_bucket_policy = Field(AWSS3BucketPolicy, 'S3 Bucket Policy')

    def add_aws_ec2_tag(self, **kwargs):
        self.aws_tags.append(AWSTagKeyValue(**kwargs))

    def add_aws_security_group(self, **kwargs):
        self.security_groups.append(AWSSecurityGroup(**kwargs))

    def add_aws_load_balancer(self, **kwargs):
        self.aws_load_balancers.append(AWSLoadBalancer(**kwargs))
