from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field


class CicsoUcmDeviceAdapter(DeviceAdapter):
    protocol = Field(str, 'Protocol')
    protocol_side = Field(str, 'Protocol Side')
    product = Field(str, 'Product')
    class_id = Field(str, 'Class')
    network_location = Field(str, 'Network Location')
    dual_mode = Field(bool, 'Dual Mode')
    protected = Field(bool, 'Protected')
