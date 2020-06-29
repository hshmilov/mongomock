from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class SalApplication(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')
    bundle_id = Field(str, 'Bundle ID')
    bundle_name = Field(str, 'Bundle Name')


class SalInventory(SmartJsonClass):
    id = Field(int, 'ID')
    version = Field(str, 'Version')
    path = Field(str, 'Path')
    application = Field(SalApplication, 'Application')


class SalDeviceInstance(DeviceAdapter):
    machine_group = Field(str, 'Machine Group')
    sal_version = Field(str, 'SAL Version')
    deployed = Field(bool, 'Deployed')
    broken_client = Field(bool, 'Broken Client')
    hd_space = Field(int, 'HD Space')
    hd_total = Field(int, 'HD Total')
    hd_percent = Field(float, 'HD Percent')
    console_user = Field(str, 'Console User')
    machine_model_friendly = Field(str, 'Machine Model Friendly')
    munki_version = Field(str, 'Munki Version')
    manifest = Field(str, 'Manifest')
    inventories = ListField(SalInventory, 'Inventories')
