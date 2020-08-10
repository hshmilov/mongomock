from datetime import datetime

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter


class OpendcimDeviceInstance(DeviceAdapter):
    dc_name = Field(str, 'Data Center Name')
    dc_id = Field(str, 'Data Center ID')
    cabinet_id = Field(str, 'Cabinet ID')
    cabinet_location = Field(str, 'Cabinet Location')
    api_port = Field(int, 'API Port')
    api_username = Field(str, 'API Username')
    asset_tag = Field(str, 'Asset Tag')
    audit_stamp = Field(datetime, 'Last Audit Timestamp')
    device_type = Field(str, 'Device Type')
    hypervisor = Field(str, 'Hypervisor')
    notes = Field(str, 'Notes')
    manufacturer_date = Field(datetime, 'Manufacturer Date')
    opendcim_owner = Field(int, 'Owner User ID')
    parent_device_id = Field(int, 'Parent Device ID')
    number_of_ports = Field(int, 'Number Of Ports')
    first_port_number = Field(int, 'First Port Number')
    position = Field(int, 'Position')
    psu_count = Field(int, 'Power Supply Unit Count')
    primary_contact = Field(int, 'Primary Contact User ID')
    rear_chassis_slots = Field(int, 'Rear Chassis Slots')
    rights = Field(str, 'Rights')
    snmp_community = Field(str, 'SNMP Community')
    snmp_failure_count = Field(int, 'SNMP Failure Count')
    snmp_version = Field(str, 'SNMP Version')
    last_reported_status = Field(str, 'Last Reported Status')
    warranty_provider = Field(str, 'Warranty Provider')
    warranty_expires = Field(datetime, 'Warranty Expires')
    v3_auth_protocol = Field(str, 'SNMP V3 Auth Protocol')
    v3_priv_protocol = Field(str, 'SNMP V3 Privacy Protocol')
    v3_security_level = Field(str, 'SNMP V3 Security Level')
    prox_mox_realm = Field(str, 'ProxMox Realm')
    escalation_id = Field(int, 'Escalation ID')
    escalation_time_id = Field(int, 'Escalation Time ID')


class OpendcimUserInstance(UserAdapter):
    read_access = Field(bool, 'Read Access')
    write_access = Field(bool, 'Write Access')
    delete_access = Field(bool, 'Delete Access')
    second_phone = Field(str, 'Second Phone')
    third_phone = Field(str, 'Third Phone')
