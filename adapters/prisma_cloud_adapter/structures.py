import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter


# pylint: disable=too-many-instance-attributes
class EC2Instance(SmartJsonClass):
    vpc_id = Field(str, 'VPC ID')
    image_id = Field(str, 'Image ID')
    subnet_id = Field(str, 'Subnet ID')
    core_count = Field(int, 'Core Count')
    threads_per_core = Field(int, 'Threads Per Core')
    hypervisor = Field(str, 'Hypervisor')
    instance_id = Field(str, 'Instance ID')
    launch_time = Field(datetime.datetime, 'Launch Time')
    monitoring = Field(bool, 'Monitoring')
    client_token = Field(str, 'Client Token')
    architecture = Field(str, 'Architecture')
    optimized_ebs = Field(bool, 'Optimized EBS')
    instance_type = Field(str, 'Instance Type')
    root_device_name = Field(str, 'Root Device Name')
    root_device_type = Field(str, 'Root Device Type')
    security_group_ids = ListField(str, 'Security Group IDs')
    security_group_names = ListField(str, 'Security Group Names')


class AzureInstance(SmartJsonClass):
    vm_id = Field(str, 'VM ID')
    location = Field(str, 'Location')
    computer_name = Field(str, 'Computer Name')
    admin_user_name = Field(str, 'Admin User Name')
    power_state = Field(str, 'Power State')
    sku = Field(str, 'SKU')


class GCPInstance(SmartJsonClass):
    id = Field(str, 'ID')
    kind = Field(str, 'Kind')
    name = Field(str, 'Name')
    vm_type = Field(str, 'VM Type')
    status = Field(str, 'Status')
    cpu_platform = Field(str, 'CPU Platform')
    description = Field(str, 'Description')
    creation_time = Field(datetime.datetime, 'Creation Time')


class SharedFields(SmartJsonClass):
    account_id = Field(str, 'Account ID')
    account_name = Field(str, 'Account Name')
    cloud_type = Field(str, 'Cloud Type')
    region_id = Field(str, 'Region ID')
    region_name = Field(str, 'Region Name')
    service = Field(str, 'Service')
    deleted = Field(bool, 'Deleted')
    has_network = Field(bool, 'Has Network')


class SecurityRule(SmartJsonClass):
    name = Field(str, 'Name')
    access = Field(str, 'Access')
    protocol = Field(str, 'Protocol')
    direction = Field(str, 'Direction')
    description = Field(str, 'Description')
    source_addresses = ListField(str, 'Source Addresses')
    destination_addresses = ListField(str, 'Destination Addresses')
    source_port_ranges = ListField(str, 'Source Port Ranges')
    destination_port_ranges = ListField(str, 'Destination Port Ranges')


class SecurityGroup(SmartJsonClass):
    vpc_id = Field(str, 'VPC ID')
    group_id = Field(str, 'Group ID')
    owner_id = Field(str, 'Owner ID')
    group_name = Field(str, 'Group Name')
    description = Field(str, 'Description')
    ip_v4_ranges_in = ListField(str, 'IP V4 In')
    ip_v6_ranges_in = ListField(str, 'IP V6 In')
    ip_v4_ranges_out = ListField(str, 'IP V4 Out')
    ip_v6_ranges_out = ListField(str, 'IP V6 Out')
    url = Field(str, 'URL')
    resource_type = Field(str, 'Resource Type')
    account = Field(str, 'Account')
    security_rules = ListField(SecurityRule, 'Security Rules')


class PrismaCloudInstance(DeviceAdapter):
    ec2_instance = Field(EC2Instance, 'EC2 Instance')
    azure_instance = Field(AzureInstance, 'Azure Instance')
    gcp_instance = Field(GCPInstance, 'GCP Instance')
    security_group = Field(SecurityGroup, 'Security Group')
    shared_fields = Field(SharedFields, 'Common Fields')
