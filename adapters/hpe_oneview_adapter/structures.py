import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class DeviceSlot(SmartJsonClass):
    device_name = Field(str, 'Device Name')
    location = Field(str, 'Location')


class HpeOneviewDeviceInstance(DeviceAdapter):
    asset_tag = Field(str, 'Asset Tag')
    capabilities = ListField(str, 'Capabilities')
    category = Field(str, 'Category')
    etag = Field(str, 'eTag')
    form_factor = Field(str, 'Form Factor')
    generation = Field(str, 'Generation')
    intelligent_provisioning_version = Field(str, 'Intelligent Provisioning Version')
    licensing_intent = Field(str, 'Licensing Intent')
    location_uri = Field(str, 'Location Uri')
    maintenance_state = Field(str, 'Maintenance State')
    maintenance_state_reason = Field(str, 'Maintenance State Reason')
    migration_state = Field(str, 'Migration State')
    modified = Field(datetime.datetime, 'Modified')
    mp_firmware_version = Field(str, 'MP Firmware Version')
    rom_version = Field(str, 'ROM Version')
    refresh_state = Field(str, 'Refresh State')
    one_time_boot = Field(str, 'One Time Boot')
    mp_model = Field(str, 'MP Model')
    mp_state = Field(str, 'MP State')
    part_number = Field(str, 'Part Number')
    physical_server_hardware_uri = Field(str, 'Physical Server Hardware Uri')
    platform = Field(str, 'Platform')
    device_slots = ListField(DeviceSlot, 'Slots')
    position = Field(str, 'Position')
    power_lock = Field(bool, 'Power Lock')
    device_state = Field(str, 'State')
    device_status = Field(str, 'Status')
