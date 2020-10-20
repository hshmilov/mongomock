import datetime

from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class BmcAtriumDeviceInstance(DeviceAdapter):
    subnet_type = Field(str, 'Subnet Type')
    subnet_name = Field(str, 'Subnet Name')
    country = Field(str, 'Country')
    ud_root_last_access_time = Field(datetime.datetime, 'UD Root Last Access Time')
    vm_power_status = Field(str, 'VM Power Status')
    managed_by_dl = Field(str, 'Managed By DL')
    device_type = Field(str, 'Device Type')
    global_id = Field(str, 'Global ID')
    bu = Field(str, 'Business Unit')
    division_project_detail = Field(str, 'Division Project Detail')
    account = Field(str, 'Account')
    owner_code = Field(str, 'Owner Code')
    it_customer = Field(str, 'IT Customer')
    bdna_model = Field(str, 'BDNA Model')
    custom_region = Field(str, 'Custom Region')
    cc_team_leader = Field(str, 'CC Team Leader')
