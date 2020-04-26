from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter


class BigidField(SmartJsonClass):
    field_name = Field(str, 'Field Name')
    field_type = Field(str, 'Field Type')
    field_value = Field(str, 'Field Value')


class BigidDeviceInstance(DeviceAdapter):
    object_type = Field(str, 'Object Type')
    container_name = Field(str, 'Container Name')
    attribute_list = ListField(str, 'Attribute List')
    full_object_name = Field(str, 'Full Object Name')
    source = Field(str, 'Source')
    total_pii_count = Field(int, 'Total PII Count')
    scanner_type_group = Field(str, 'Scanner Type Group')
    open_access = Field(str, 'Open Access')
    full_fields = ListField(BigidField, 'Full Fields')
