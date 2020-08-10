from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter


class LogmeinDeviceInstance(DeviceAdapter):
    is_host_online = Field(bool, 'Online Host')
    asset_tag = Field(str, 'Asset Tag')


class LogmeinUserInstance(UserAdapter):
    is_master_account_holder = Field(bool, 'Master Account Holder')
