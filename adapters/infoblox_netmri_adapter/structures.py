# pylint:disable=unused-import
import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter


class InfobloxNetmriDeviceInstance(DeviceAdapter):
    extra_info = Field(str, 'Additional Info',
                       description='Additional information about the device; '
                       'IP phones will contain the extension in this field.')  # DeviceAddlInfo
    assurance = Field(int, 'Assurance Level',
                      description='The assurance level of the device type value.')  # DeviceAssurance
    collector = Field(int, 'NetMRI Collector ID')  # DataSourceID
    netbios_name = Field(str, 'Device NetBIOS Name')  # DeviceNetBIOSName
    device_type = Field(str, 'Device Type')  # DeviceType
    parent_id = Field(int, 'Parent Device ID')  # ParentDeviceID
    unique_key = Field(str, 'Device Unique Key')  # DeviceUniqueKey
    is_infra = Field(bool, 'Is Infrastructure Device')  # InfraDeviceInd
    is_network = Field(bool, 'Is Network Device')  # NetworkDeviceInd
    is_virtual = Field(bool, 'Is Virtual Device')  # VirtualInd
    snmp_sysdescr = Field(str, 'SNMP SysDescr')  # DeviceSysDescr
    snmp_syslocation = Field(str, 'SNMP SysLocation')  # DeviceSysLocation
    snmp_sysname = Field(str, 'SNMP SysName')  # DeviceSysName
    dns_name = Field(str, 'Device DNS Name')  # DeviceDNSName
    rev_start_time = Field(datetime.datetime, 'Revision Start Time')  # DeviceStartTime
    rev_end_time = Field(datetime.datetime, 'Revision End Time')  # DeviceEndTime
    mgmt_server_id = Field(int, 'Management Server Device ID')  # MgmtServerDeviceID
    virtual_net_id = Field(int, 'Internal NetMRI Virtual Network ID')  # VirtualNetworkID
