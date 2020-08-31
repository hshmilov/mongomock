from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class GigamonFmDeviceInstance(DeviceAdapter):
    dns_name = Field(str, 'DNS Name')
    cluster_mode = Field(str, 'Cluster Mode')
    cluster_id = Field(str, 'Cluster ID')
