import datetime

from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class AlcideDeviceInstance(DeviceAdapter):
    uid = Field(str, 'UID')
    namespace = Field(str, 'Namespace')
    monitor_time = Field(datetime.datetime, 'Monitor Time')
    agent_time = Field(datetime.datetime, 'Agent Time')
    monitor_active = Field(bool, 'Monitor Active')
    agent_active = Field(bool, 'Agent Active')
    datacenter = Field(str, 'Datacenter')
    cluster = Field(str, 'Cluster')
    label = Field(str, 'Label')
    meta_type = Field(str, 'Meta Type')
    boot_id = Field(str, 'Boot ID')
    virtualization_engine = Field(str, 'Virtualization Engine')
    virtualization_version = Field(str, 'Virtualization Version')
    images = Field(str, 'Images')
    node_agent_version = Field(str, 'Node Agent Version')
    orchestrator_type = Field(str, 'Orchestrator Type')
    orchestration_agent_version = Field(str, 'Orchestration Agent Version')
