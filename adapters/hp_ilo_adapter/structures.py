from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


# pylint: disable=too-many-instance-attributes
class HPILOInstance(DeviceAdapter):
    asset_tag = Field(str, 'Asset Tag')
    host_fqdn = Field(str, 'Host FQDN')
    host_correlation_name = Field(str, 'Host Correlation Name')
    indicator_led = Field(str, 'Indicator LED')
    processor_model = Field(str, 'Processor Model')
    power = Field(str, 'Power')
    power_status = Field(str, 'Power Status')
    sku = Field(str, 'SKU')
    system_type = Field(str, 'System Type')
