from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils import datetime


class GigamonFmDeviceInstance(DeviceAdapter):
    dns_name = Field(str, 'DNS Name')
    cluster_mode = Field(str, 'Cluster Mode')
    cluster_id = Field(str, 'Cluster ID')
    behind_NAT = Field(bool, 'Behind NAT')
    box_id = Field(str, 'Box ID')
    cluster_master = Field(str, 'Cluster Master')
    cluster_virtual_ip = Field(str, 'Cluster Virtual IP')
    disc_outcome = Field(str, 'Disc Outcome')
    family = Field(str, 'Family')
    global_node_id = Field(str, 'Global Node ID')
    health_state = Field(str, 'Health State')
    last_sync_time = Field(datetime.datetime, 'Last Sync Time')
    licensed = Field(bool, 'Licensed')
    operational_status = Field(str, 'Operational Status')
    sw_version = Field(str, 'Software Version')
    topo_node_id = Field(str, 'Topo Node ID')
    uboot_version = Field(str, 'Uboot Version')
