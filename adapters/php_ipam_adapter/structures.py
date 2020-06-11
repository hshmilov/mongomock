import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter


# pylint: disable=too-many-instance-attributes
class Subnet(SmartJsonClass):
    id = Field(str, 'ID')
    subnet = Field(str, 'Subnet')
    mask = Field(str, 'Mask')
    description = Field(str, 'Description')
    section_id = Field(str, 'Section ID')
    linked_subnet = Field(str, 'Linked Subnet')
    device_id = Field(str, 'device_id')
    vlan_id = Field(str, 'VLAN ID')
    vrf_id = Field(str, 'VRF ID')
    master_subnet_id = Field(str, 'Master Subnet ID')
    name_server_id = Field(str, 'Name Server ID')
    show_name = Field(str, 'Show Name')
    permissions = Field(str, 'Permissions')
    resolve_dns = Field(str, 'Resolve DNS')
    dns_recursive = Field(str, 'DNS Recursive')
    dns_records = Field(str, 'DNS Recoreds')
    allow_requests = Field(str, 'Allow Requests')
    scan_agent = Field(str, 'Scan Agnet')
    ping_subnet = Field(str, 'Ping Subnet')
    discover_subnet = Field(str, 'Discover Subnet')
    is_folder = Field(bool, 'Is Folder')
    is_full = Field(bool, 'Is Full')
    tag = Field(str, 'Tag')
    state = Field(str, 'State')
    firewall_address_object = Field(str, 'Firewall Address Object')
    location = Field(str, 'Location')


class PhpIpamDeviceInstance(DeviceAdapter):
    rack_size = Field(int, 'Rack Size')
    snmp_v3_priv_pass = Field(str, 'SNMP V3 Priv Pass')
    snmp_community = Field(str, 'SNMP Community')
    snmp_v3_priv_protocol = Field(str, 'SNMP V3 Priv Protocol')
    sections = Field(str, 'Sections')
    snmp_v3_ctx_name = Field(str, 'SNMP V3 CTX Name')
    snmp_v3_sec_level = Field(str, 'SNMP V3 Sec Level')
    edit_date = Field(datetime.datetime, 'Edit Date')
    rack_start = Field(int, 'Rack Start')
    snmp_version = Field(str, 'SNMP Version')
    snmp_queries = Field(str, 'SNMP Queries')
    snmp_v3_auth_pass = Field(str, 'SNMP V3 Auth Pass')
    snmp_timeout = Field(int, 'SNMP Timeout')
    rack = Field(int, 'Rack')
    snmp_v3_ctx_engine_id = Field(str, 'SNMP V3 CTX Engine ID')
    snmp_v3_auth_protocol = Field(str, 'SNMP V3 Auth Protocol')
    device_type = Field(int, 'Type')
    snmp_port = Field(int, 'SNMP Port')
    vendor = Field(str, 'Vendor')
    subnets = ListField(Subnet, 'Subnets')


class PhpIpamUserInstance(UserAdapter):
    # TBD, after testing check values and add
    pass
