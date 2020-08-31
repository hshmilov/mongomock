from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class IvantiEndpointSecurityDeviceInstance(DeviceAdapter):
    status = Field(str, 'Status')
    manifest_version = Field(str, 'Manifest Version')
