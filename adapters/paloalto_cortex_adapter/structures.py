from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


# pylint: disable=too-many-instance-attributes
class GlobalProtectDevice(DeviceAdapter):
    customer_id = Field(str, 'Customer ID')
    serial_number = Field(str, 'Serial Number')
    connect_method = Field(str, 'Connect Method')
    host_id = Field(str, 'Host ID')
    source_user = Field(str, 'Source Use')
    event_status = Field(str, 'Event Status')
    vendor_name = Field(str, 'Vendor Name')
