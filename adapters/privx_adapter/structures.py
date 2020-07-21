from datetime import datetime
from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter

# These fields are the most basic fields that exist for local uysers/devices
# For other PrivX servers might have more fields of AD/OpenID if they integrated with those products.


class PrivxDeviceInstance(DeviceAdapter):
    addresses = ListField(str, 'Addresses')


class PrivxUserInstance(UserAdapter):
    password_change_required = Field(bool, 'Password Change Required')
    user_update_time = Field(datetime, 'Last Updated')
    windows_account = Field(str, 'Windows Account')
    unix_account = Field(str, 'Unix Account')
