import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class ProductData(SmartJsonClass):
    product_name = Field(str, 'Product Name')
    product_version = Field(str, 'Prodcut Version')
    last_updated = Field(datetime.datetime, 'Last Updated')
    last_action_status = Field(str, 'Last Action Status')
    sku = Field(str, 'Sku')
    application_id = Field(str, 'Application Id')
    product_key_id = Field(str, 'Product Key Id')
    product_description = Field(str, 'Product Description')


class MicrosoftKmsDeviceInstance(DeviceAdapter):
    products_data = ListField(ProductData, 'Products')
