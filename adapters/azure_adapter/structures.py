import logging
from datetime import datetime

from axonius.clients.azure.structures import AzureAdapterEntity
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass


logger = logging.getLogger(f'axonius.{__name__}')


class AzureImage(SmartJsonClass):
    publisher = Field(str, 'Image Publisher')
    offer = Field(str, 'Image Offer')
    sku = Field(str, 'Image SKU')
    version = Field(str, 'Image Version')
    exact_version = Field(str, 'Exact Version')


class AzureNetworkSecurityGroupRule(SmartJsonClass):
    iface_name = Field(str, 'Interface Name')
    access = Field(str, 'Access')
    description = Field(str, 'Description')
    direction = Field(str, 'Direction')
    rule_id = Field(str, 'ID')
    name = Field(str, 'Name')
    priority = Field(int, 'Priority')
    protocol = Field(str, 'Protocol')
    source_address_prefixes = ListField(str, 'Source Address Prefixes')
    source_port_ranges = ListField(str, 'Source Port Ranges')
    destination_address_prefixes = ListField(str, 'Destination Address Prefixes')
    destination_port_ranges = ListField(str, 'Destination Port Ranges')
    is_default = Field(bool, 'Is Default')


class AzureSoftwareUpdate(SmartJsonClass):
    id = Field(str, 'ID')
    name = Field(str, 'Name')
    automation_account_name = Field(str, 'Automation Account Name')
    location = Field(str, 'Location')
    operating_system = Field(str, 'Operating System')
    duration = Field(str, 'Duration')
    frequency = Field(str, 'Frequency')
    provisioning_state = Field(str, 'Provisioning State')
    start_time = Field(datetime, 'Start Time')
    creation_time = Field(datetime, 'Creation Time')
    last_modified_time = Field(datetime, 'Last Modified')
    next_run = Field(datetime, 'Next Run')


class AzureDeviceInstance(DeviceAdapter, AzureAdapterEntity):
    cloud_name = Field(str, 'Cloud Name')
    account_tag = Field(str, 'Account Tag')
    location = Field(str, 'Azure Location')
    instance_type = Field(str, 'Azure Instance Type')
    image = Field(AzureImage, 'Image')
    admin_username = Field(str, 'Admin Username')
    vm_id = Field(str, 'VM ID')
    azure_firewall_rules = ListField(AzureNetworkSecurityGroupRule, 'Azure Firewall Rules')
    resources_group = Field(str, 'Resource Group')
    custom_image_name = Field(str, 'Custom Image Name')
    subscription_id = Field(str, 'Azure Subscription ID')
    subscription_name = Field(str, 'Azure Subscription Name')
    virtual_networks = ListField(str, 'Virtual Networks')
    software_updates = ListField(AzureSoftwareUpdate, 'Software Updates')
