import datetime

from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter


class SecurityGroup(SmartJsonClass):
    id = Field(int, 'ID')
    user_name = Field(str, 'Username')
    description = Field(str, 'Description')
    create_date = Field(datetime.datetime, 'Create Date')
    state = Field(str, 'State')
    name = Field(str, 'Name')


class SymantecDcsDeviceInstance(DeviceAdapter):
    category_name = Field(str, 'Category Name')
    security_group = Field(SecurityGroup, 'Security Group')
    manager_name = Field(str, 'Manager Name')
    agent_status = Field(str, 'Agent Status')
    agent_state = Field(str, 'Agent State')
    guid = Field(str, 'GUID')
    element_type = Field(str, 'Element Type')
