from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class PuppetInstance(DeviceAdapter):
    version = Field(str, 'Puppet Version')
    aio_agent_build = Field(str, 'AIO Agent Build')
    aio_agent_version = Field(str, 'AIO Agent Version')
    datacenter = Field(str, 'Data Center')
    ecp_role = Field(str, 'ECP Role')
    facts_environment = Field(str, 'Facts Environment')
    net_zone = Field(str, 'Net Zone')
    kernel = Field(str, 'Kernel')
    kernel_version = Field(str, 'Kernel Version')
    kernel_release = Field(str, 'Kernel Release')
    fqdn = Field(str, 'FQDN')
    operating_system = Field(str, 'Operating System')
    operating_system_release_version = Field(str, 'Operating System Release Version')
    operating_system_release = Field(str, 'Operating System Release')
