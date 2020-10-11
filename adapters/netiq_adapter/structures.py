from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class NetiqDeviceInstance(DeviceAdapter):
    software_type = Field(str, 'Software Type')
    device_type = Field(int, 'Type')
    trusted = Field(bool, 'Trusted')
    local = Field(bool, 'Local')
    device_id = Field(str, 'Device ID')
    software_version = Field(str, 'Software Version')
