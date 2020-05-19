import datetime
from enum import Enum, auto

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter
from aws_adapter.connection.structures import OnlyAWSDeviceAdapter


class GNAApiDeviceType(Enum):
    AWSEC2 = auto()


class GNaapiRelationships(SmartJsonClass):
    relationship_name = Field(str, 'Relationship Name')
    resource_id = Field(str, 'Resource ID')
    resource_name = Field(str, 'Resource Name')
    resource_type = Field(str, 'Resource Type')


class GNaapiDeviceInstance(DeviceAdapter):
    aws_data = Field(OnlyAWSDeviceAdapter, 'AWS Data')
    g_naapi_index_date = Field(datetime.datetime, 'Index Date')
    g_naapi_ttl = Field(datetime.datetime, 'TTL')
    relationships = ListField(GNaapiRelationships, 'Relationships')


class GNaapiUserInstance(UserAdapter):
    pass
