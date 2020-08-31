from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class SymantecEdrDeviceInstance(DeviceAdapter):
    disposition_endpoint = Field(str, 'Disposition Endpoint')
    managed_sepm_ip = Field(str, 'Managed SEPM IP')
    managed_sepm_version = Field(str, 'Managed SEPM Version')
    sep_group_name = Field(str, 'SEP Group Name')
    sep_domain_name = Field(str, 'SEP Domain Name')
