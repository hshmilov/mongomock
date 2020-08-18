from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class CheckmarxDeviceInstance(DeviceAdapter):
    uri = Field(str, 'URI')
    min_loc = Field(int, 'Min Loc')
    max_loc = Field(int, 'Max Loc')
    max_scans = Field(int, 'Max Scans')
    cx_version = Field(str, 'CX Version')
    cx_status = Field(str, 'CX Status')
