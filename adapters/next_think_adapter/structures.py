import datetime

from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter


class NextThinkDeviceInstance(DeviceAdapter):
    antispyware_name = Field(str, 'Main Antispyware')
    antivirus_name = Field(str, 'Main Antivirus')
    chassis_serial_number = Field(str, 'Chassis Serial Number')
    device_password_required = Field(bool, 'Password Required')
    device_product_id = Field(str, 'Product ID')
    device_product_version = Field(str, 'Product Version')
    distinguished_name = Field(str, 'Distinguished Name')
    entity = Field(str, 'Entity')
    firewall_name = Field(str, 'Main Firewall')
    group_name = Field(str, 'Group Name')
    platform = Field(str, 'Platform', enum=['Windows', 'Mac OS', 'Mobile'])
    sid = Field(str, 'SID')


class NextThinkUserInstance(UserAdapter):
    distinguished_name = Field(str, 'Distinguished Name')
    first_seen = Field(datetime.datetime, 'First Seen')
    number_of_days_since_last_seen = Field(int, 'Days Since Last Seen')
    full_name = Field(str, 'Full Name')
    seen_on_mac = Field(bool, 'Seen On Mac')
    seen_on_mobile = Field(bool, 'Seen On Mobile')
    seen_on_windows = Field(bool, 'Seen On Windows')
    total_active_days = Field(int, 'Total Active Days')
    user_type = Field(str, 'Type', enum=['local', 'domain', 'system'])
    user_uid = Field(str, 'UID')
