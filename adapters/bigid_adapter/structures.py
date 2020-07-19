from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter


class CatalogData(SmartJsonClass):
    catalog_name = Field(str, 'Catalog Name')
    object_type = Field(str, 'Object Type')
    container_name = Field(str, 'Container Name')
    attribute_list = ListField(str, 'Attribute List')
    full_object_name = Field(str, 'Full Object Name')
    source = Field(str, 'Source')
    total_pii_count = Field(int, 'Total PII Count')
    avg = Field(int, 'Average Risk')
    scanner_type_group = Field(str, 'Scanner Type Group')
    open_access = Field(str, 'Open Access')


class BigidDeviceInstance(DeviceAdapter):
    catalogs_data = ListField(CatalogData, 'Catalogs Data')
