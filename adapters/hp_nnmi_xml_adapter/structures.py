import datetime

from axonius.fields import Field, ListField, JsonStringFormat
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import format_ip, format_ip_raw


class ExtendedAttribute(SmartJsonClass):
    name = Field(str, 'Name')
    val = Field(str, 'Value')


class NNMIInterface(SmartJsonClass):
    iface_id = Field(str, 'ID')
    uuid = Field(str, 'UUID')
    name = Field(str, 'Name')
    alias = Field(str, 'Alias')
    iface_type = Field(int, 'Type')
    iface_index = Field(int, 'Index')
    description = Field(str, 'Description')
    physical_addr = Field(str, 'Physical Address')
    cdp = Field(str, 'CDP')
    speed = Field(str, 'Speed')
    created = Field(datetime.datetime, 'Created')
    modified = Field(datetime.datetime, 'Modified')
    status = Field(str, 'Status')
    mgmt_mode = Field(str, 'Management Mode')
    mgmt_state = Field(str, 'Management State')
    capabilities = ListField(str, 'Capabilities')
    ext_attrs = ListField(ExtendedAttribute, 'Extended Attributes')
    ips = ListField(str, 'IP Addresses', converter=format_ip, json_format=JsonStringFormat.ip)
    ips_raw = ListField(str, converter=format_ip_raw, hidden=True)


class HPNNMIDeviceInstance(DeviceAdapter):
    status = Field(str, 'Status')
    management_mode = Field(str, 'Management Mode')
    system_contact = Field(str, 'System Contact')
    location = Field(str, 'Location')
    snmp_name = Field(str, 'Node SNMP Name')
    snmp_addr = Field(str, 'SNMP Address', converter=format_ip, json_format=JsonStringFormat.ip)
    snmp_addr_raw = ListField(str, converter=format_ip_raw, hidden=True)
    system_object_id = Field(str, 'System Object ID')
    notes = Field(str, 'Notes')
    created = Field(datetime.datetime, 'Creation time')
    modified = Field(datetime.datetime, 'Last Modified')
    status_change = Field(datetime.datetime, 'Last Status Change')
    proto_ver = Field(str, 'Protocol Version')
    discovery_state = Field(str, 'Discovery State')
    device_description = Field(str, 'Device Description')
    device_category = Field(str, 'Device Category')
    capabilities = ListField(str, 'Capabilities')
    pwr_state = Field(str, 'Device Power State')
    last_state_change = Field(datetime.datetime, 'Last State Change')
    ext_attrs = ListField(ExtendedAttribute, 'Extended Attributes')
    ifaces = ListField(NNMIInterface, 'Interface Data')
