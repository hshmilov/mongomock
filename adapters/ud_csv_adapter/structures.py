from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter


class UdCsvDeviceInstance(DeviceAdapter):
    region = Field(str, 'Region')
    it_customer = Field(str, 'IT Customer')
    division_name = Field(str, 'Division Name')
    country_name = Field(str, 'Country Name')
    all_ips = ListField(str, 'All IPs')
    cmdb_id = Field(str, 'CMDB ID')
    vm_status = Field(str, 'VM Status')
    device_type = Field(str, 'Device Type')
    comment = Field(str, 'Comment')
    contact_person = Field(str, 'Contact Person')
    bucategory = Field(str, 'BU Category')
    team_leader = Field(str, 'Team Leader')
