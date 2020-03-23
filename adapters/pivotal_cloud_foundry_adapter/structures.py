from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class PivotalCloudFoundryInstance(DeviceAdapter):
    container_age = Field(int, 'Container Age (Seconds)')
    state = Field(str, 'State')
    type = Field(str, 'Type')
