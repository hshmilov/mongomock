from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class CiscoSecurityManagerDeviceInstance(DeviceAdapter):
    image_name = Field(str, 'Image Name')
    device_type = Field(str, 'Device Type')
