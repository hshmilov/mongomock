from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter


class Policy(SmartJsonClass):
    id = Field(str, 'ID')
    guid = Field(str, 'GUID')
    name = Field(str, 'Name')
    description = Field(str, 'Description')
    platform_type = Field(str, 'Platform Type')


class BeyondTrustDeviceInstance(DeviceAdapter):
    domain_id = Field(str, 'Domain ID')
    host_sid = Field(str, 'Host SID')
    name_netbios = Field(str, 'Name NetBIOS')
    chassis_type = Field(str, 'Chassis Type')
    os_product_type = Field(str, 'OS Product Type')
    policy = Field(Policy, 'Policy')


class BeyondTrustUserInstance(UserAdapter):
    domain_id = Field(str, 'Domain ID')
    last_logon_id = Field(str, 'Logon ID')
    is_power_user = Field(bool, 'Is Power User')
    ui_language = Field(str, 'UI Language')
    locale = Field(str, 'Locale')
    last_used_host_id = Field(str, 'Last Used Host ID')
    policy = Field(Policy, 'Policy')
