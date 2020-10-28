import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass
from axonius.clients.flexnet.consts import INVENTORY_TYPE, DEVICE_TYPE


class Asset(SmartJsonClass):
    department = Field(str, 'Department')
    company = Field(str, 'Company')
    name = Field(str, 'Name')
    asset_id = Field(int, 'ID')
    tag = Field(str, 'Tag')
    asset_type = Field(str, 'Type')
    category = Field(str, 'Category')
    expiration_date = Field(datetime.datetime, 'Expiration Date')
    installation_date = Field(datetime.datetime, 'Installation Date')
    manufacturer = Field(str, 'Manufacturer')
    model_number = Field(str, 'Model Number')
    serial_number = Field(str, 'Serial Number')
    status = Field(str, 'Status')


class FlexnetDeviceInstance(DeviceAdapter):
    assets = ListField(Asset, 'Assets')
    device_type = Field(str, 'Device Type',
                        enum=['Computer', 'Container Image', 'Mobile Device', 'Remote Device', 'VDI Template',
                              'Virtual Machine', 'VM Host'])
    device_kind = Field(str, 'Device Kind', enum=[DEVICE_TYPE, INVENTORY_TYPE])
