from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


# pylint: disable=too-many-instance-attributes
class AccessPointInstance(SmartJsonClass):
    swarm_id = Field(str, 'Swarm ID')
    group_name = Field(str, 'Group Name')
    cluster_id = Field(str, 'Cluster ID')
    deployment_mode = Field(str, 'Deployment Mode')
    status = Field(str, 'Status')
    swarm_master = Field(bool, 'Swarm Master')
    down_reason = Field(str, 'Down Reason')
    mesh_role = Field(str, 'Mesh Role')
    mode = Field(str, 'Mode')
    client_counts = Field(int, 'Client Counts')
    ssid_count = Field(int, 'SSID Count')
    modem_connected = Field(bool, 'Modem Connected')


class SwitchInstance(SmartJsonClass):
    group_name = Field(str, 'Group Name')
    status = Field(str, 'Status')
    mode = Field(int, 'Mode')
    total_clients = Field(int, 'Total Clients')
    max_power = Field(int, 'Max Power')
    power_consumption = Field(int, 'Power Consumption')
    fan_speed = Field(str, 'Fan Speed')
    temperature = Field(str, 'Temperature')
    site = Field(str, 'Site')
    switch_type = Field(str, 'Type')


class ArubaCentralDeviceInstance(DeviceAdapter):
    switch = Field(SwitchInstance, 'Switch')
    access_point = Field(AccessPointInstance, 'Access Point')
