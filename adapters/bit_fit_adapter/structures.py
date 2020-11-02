import datetime

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter


class AssetLocation(SmartJsonClass):
    ids = ListField(int, 'IDs')
    name = Field(str, 'Name')


class AssetType(SmartJsonClass):
    id = Field(int, 'ID')
    label = Field(str, 'Label')


class BitFitDeviceInstance(DeviceAdapter):
    shelf = Field(int, 'Shelf')
    size = Field(int, 'Size')
    side = Field(str, 'Side')
    lease_info = Field(str, 'Lease Info')
    lease_date = Field(datetime.datetime, 'Lease Date')
    lease_expiration_date = Field(datetime.datetime, 'Lease Expiration Date')
    vendor_ssd = Field(str, 'Vendor SSD')
    vendor_ram = Field(str, 'Vendor RAM')
    depth = Field(str, 'Depth')
    asset_location = Field(AssetLocation, 'Location')
    asset_type = Field(AssetType, 'Type')
    created_at = Field(datetime.datetime, 'Created At')
    updated_at = Field(datetime.datetime, 'Updated At')


class BitFitUserInstance(UserAdapter):
    pass
