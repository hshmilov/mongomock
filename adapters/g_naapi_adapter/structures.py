import datetime
from enum import Enum, auto

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter
from aws_adapter.connection.structures import OnlyAWSDeviceAdapter
from azure_adapter.structures import OnlyAzureDeviceInstance


class GNAApiDeviceType(Enum):
    AWSEC2 = auto()
    AzureCompute = auto()
    GEIXCompute = auto()


class GNaapiRelationships(SmartJsonClass):
    relationship_name = Field(str, 'Relationship Name')
    resource_id = Field(str, 'Resource ID')
    resource_name = Field(str, 'Resource Name')
    resource_type = Field(str, 'Resource Type')


class GEIXComputeServer(SmartJsonClass):
    region = Field(str, 'Region')
    account_id = Field(str, 'Account ID')
    account_alias = Field(str, 'AccountAlias')
    availability_zone = Field(str, 'Availability Zone')
    instance_name = Field(str, 'Instance Name')
    key_name = Field(str, 'Key Name')
    project_id = Field(str, 'Project ID')
    host_id = Field(str, 'Host ID')
    host_status = Field(str, 'Host Status')
    created_at = Field(datetime.datetime, 'Created At')
    vm_state = Field(str, 'VM State')
    owner_name = Field(str, 'Owner Name')


class GNaapiAzureDeviceInstance(OnlyAzureDeviceInstance):
    plan = Field(str, 'plan')


class GNaapiDeviceInstance(DeviceAdapter):
    aws_data = Field(OnlyAWSDeviceAdapter, 'AWS Data')
    azure_data = Field(GNaapiAzureDeviceInstance, 'Azure Data')
    geix_data = Field(GEIXComputeServer, 'GEIX Data')
    g_naapi_index_date = Field(datetime.datetime, 'Index Date')
    g_naapi_ttl = Field(datetime.datetime, 'TTL')
    g_naapi_configuration_item_capture_time = Field(datetime.datetime, 'Configuration Item Capture Time')
    g_naapi_source = Field(str, 'Naapi Source')
    harvest_date = Field(datetime.datetime, 'HarvestDate')
    relationships = ListField(GNaapiRelationships, 'Relationships')


class GNaapiUserInstance(UserAdapter):
    pass
