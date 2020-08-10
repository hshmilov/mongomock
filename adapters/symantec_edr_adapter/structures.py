from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class SymantecEdrDeviceInstance(DeviceAdapter):
    ip_address = Field(str, 'IP Address')
    agent_version = Field(str, 'Agent Version')
    disposition_endpoint = Field(str, 'Disposition Endpoint')
    domain_or_workgroup = Field(str, 'Domain/Workgroup')
    managed_sepm_ip = Field(str, 'Managed SEPM IP')
    managed_sepm_version = Field(str, 'Managed SEPM Version')
    os_architecture = Field(str, 'OS Architecture')
    sep_group_name = Field(str, 'SEP Group Name')
    sep_domain_name = Field(str, 'SEP Domain Name')
