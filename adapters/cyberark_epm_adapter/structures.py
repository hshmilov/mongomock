import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class Application(SmartJsonClass):
    app_type = Field(str, 'Type')
    description = Field(str, 'Description')
    name = Field(str, 'Name')
    location = Field(str, 'Location')
    owner = Field(str, 'Owner')


class Policy(SmartJsonClass):
    id = Field(str, 'ID')
    policy_type = Field(str, 'Type')
    name = Field(str, 'Name')
    action = Field(str, 'Action')
    description = Field(str, 'Description')
    active = Field(bool, 'Active')
    create_time = Field(datetime.datetime, 'Create Time')
    update_time = Field(datetime.datetime, 'Update Time')
    priority = Field(int, 'Priority')
    applications = ListField(Application, 'Applications')


class Set(SmartJsonClass):
    id = Field(str, 'ID')
    name = Field(str, 'Name')
    description = Field(str, 'Description')
    is_npvdi = Field(bool, 'Is NPVDI')


class CyberarkEpmDeviceInstance(DeviceAdapter):
    device_type = Field(str, 'Type')
    status = Field(str, 'Status')
    set_obj = Field(Set, 'Set')
    policy = Field(Policy, 'Policy')
