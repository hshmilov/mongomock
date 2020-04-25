import datetime

from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class ExtraHopInstance(DeviceAdapter):
    mod_time = Field(datetime.datetime, 'Mod Time')
    node_id = Field(int, 'Node ID')
    extrahop_id = Field(str, 'ExtraHop ID')
    user_mod_time = Field(datetime.datetime, 'User Mod Time')
    parent_id = Field(str, 'Parent ID')
    vendor = Field(str, 'Vendor')
    is_l3 = Field(bool, 'Is L3')
    device_class = Field(str, 'Device Class')
    default_name = Field(str, 'Default Name')
    custom_name = Field(str, 'Custom Name')
    cdp_name = Field(str, 'CDP Name')
    netbios_name = Field(str, 'Net Bios Name')
    custom_type = Field(str, 'Custom Type')
    analysis_level = Field(int, 'Analysis Level')
    role = Field(str, 'Role')
    critical = Field(bool, 'Critical')
    display_name = Field(str, 'Display Name')
