from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field


class FailoverClusterDeviceInstance(DeviceAdapter):
    cluster_name = Field(str, 'Cluster Name')
    cluster_node_name = Field(str, 'Cluster Node Name')
    cluster_node_id = Field(int, 'Cluster Node ID')
    cluster_node_state = Field(str, 'Cluster Node State')
