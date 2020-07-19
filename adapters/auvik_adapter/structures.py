import datetime

from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class AuvikDeviceInstance(DeviceAdapter):
    online_status = Field(str, 'Online Status')
    last_modified = Field(datetime.datetime, 'Last Modified')
    firmware_version = Field(str, 'Firmware Version')
    software_version = Field(str, 'Software Version')
    device_type = Field(str, 'Device Type')
    manage_status = Field(bool, 'Manage Status')
    traffic_insights_status = Field(str, 'Traffic Insights Status')
    discovery_snmp = Field(str, 'Discovery SNMP')
    discovery_login = Field(str, 'Discovery Login')
    discovery_wmi = Field(str, 'Discovery WMI')
    discovery_vmware = Field(str, 'Discovery VMware')
