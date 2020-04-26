from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField


class NozomiAssetDevice(DeviceAdapter):
    level = Field(str, 'SCADA Level (Purdue-model)')
    roles = ListField(str, 'roles')
    product_name = Field(str, 'Product Name')
    firmware_version = Field(str, 'Firmware Version')
    appliance_hosts = ListField(str, 'Appliance Hosts')
    capture_device = Field(str, 'Capture Device')
    asset_type = Field(str, 'Asset Type')
    protocols = ListField(str, 'Protocols Used From/To Node')
