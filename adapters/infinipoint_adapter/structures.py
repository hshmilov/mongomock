from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter


class InfinipointDeviceInstance(DeviceAdapter):
    edge = Field(bool, 'Edge')
    product_type = Field(str, 'Product Type')
    device_tags = ListField(str, 'Device Tags')
    policy_version = Field(str, 'Policy Version')
    client_type = Field(str, 'Client Type')
