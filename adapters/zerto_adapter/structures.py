from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class ZertoDeviceInstance(DeviceAdapter):
    identifier = Field(str, 'Identifier')
    status = Field(str, 'Status')
    protected_site_name = Field(str, 'Protected Site Name')
    protected_site_type = Field(str, 'Protected Site Type')
    protected_site_role = Field(str, 'Protected Site Role')
    recovery_site_name = Field(str, 'Recovery Site Name')
    recovery_site_type = Field(str, 'Recovery Site Type')
    recovery_site_role = Field(str, 'Recovery Site Role')
