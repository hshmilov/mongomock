from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class PhysicalPort(SmartJsonClass):
    id = Field(str, 'ID')
    number = Field(str, 'Number')
    name = Field(str, 'Name')
    port_type = Field(str, 'Type', enum=['ACCESS', 'INTERSWITCH', 'OTHER', 'HOST', 'BPECASCADE', 'MLAG_ISC'])
    alias = Field(str, 'Alias')
    speed = Field(str, 'Speed',
                  enum=['UNKNOWN', 'TEN', 'SPEED_TEN100', 'SPEED_1GIG', 'SPEED_2DECIMAL5GIG', 'SPEED_5GIG',
                        'SPEED_10GIG', 'SPEED_25GIG', 'SPEED_40GIG', 'SPEED_50GIG', 'SPEED_100GIG', 'INFINIBAND_SPEED',
                        'AUTO'])
    default_policy = Field(str, 'Default Policy')
    vlan_id = Field(str, 'VLAN ID')


class ExtremeNetworksExtremeControlDeviceInstance(DeviceAdapter):
    system_object_identifier = Field(str, 'System Object ID')
    site_id = Field(str, 'Site ID')
    physical_ports = ListField(PhysicalPort, 'Physical Ports')
    hardware_mode = Field(str, 'Hardware Mode', enum=['SWITCH', 'CB', 'BPE'])
    slot_number = Field(str, 'Slot Number')
    host_site = Field(str, 'Host Site')
    software_version = Field(str, 'Software Version')
