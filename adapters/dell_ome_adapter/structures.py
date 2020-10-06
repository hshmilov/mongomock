import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class ServerCard(SmartJsonClass):
    id = Field(int, 'ID')
    slot_number = Field(str, 'Card Slot Number')
    manufacturer = Field(str, 'Manufacturer')
    description = Field(str, 'Description')
    databus_width = Field(str, 'Databus Width')
    slot_length = Field(str, 'Slot Length')
    slot_type = Field(str, 'Slot Type')


# pylint: disable=too-many-instance-attributes
class ServerProcessor(SmartJsonClass):
    id = Field(int, 'ID')
    family = Field(str, 'Family')
    max_speed = Field(int, 'Max Speed')
    current_speed = Field(int, 'Current Speed')
    slot_number = Field(str, 'Process Slot Number')
    status = Field(int, 'Status')
    number_of_cores = Field(int, 'Number Of Cores')
    number_of_enabled_cores = Field(int, 'Number Of Enabled Cores')
    brand_name = Field(str, 'Brand Name')
    model_name = Field(str, 'Model Name')
    instance_id = Field(str, 'Instance ID')
    voltage = Field(str, 'Voltage')


class HostName(SmartJsonClass):
    id = Field(int, 'ID')
    host_name = Field(str, 'Hostname')


# pylint: disable=too-many-instance-attributes
class ArrayDisk(SmartJsonClass):
    id = Field(int, 'ID')
    device_id = Field(int, 'Device ID')
    disk_number = Field(str, 'Disk Number')
    vendor_name = Field(str, 'Vendor Name')
    status = Field(int, 'Status')
    status_string = Field(str, 'Status String')
    model_number = Field(str, 'Model Number')
    serial_number = Field(str, 'Serial Number')
    revision = Field(str, 'Revision')
    enclosure_id = Field(str, 'Enclosure ID')
    channel = Field(int, 'Channel')
    size = Field(str, 'Size')
    free_space = Field(str, 'Free Space')
    used_space = Field(str, 'Used Space')
    bus_type = Field(str, 'Bus Type')
    slot_number = Field(int, 'Slot Number')
    media_type = Field(str, 'Media Type')
    remaining_read_write_endurance = Field(str, 'Remaining Read Write Endurance')
    security_state = Field(str, 'Security State')


class RaidControl(SmartJsonClass):
    id = Field(int, 'ID')
    device_id = Field(int, 'Device ID')
    name = Field(str, 'Name')
    fqdd = Field(str, 'FQDD')
    status = Field(int, 'Status')
    status_type_string = Field(str, 'Status Type String')
    rollup_status = Field(int, 'Rollup Status')
    rollup_status_string = Field(str, 'Rollup Status String')
    cache_size_mb = Field(int, 'Cache Size (MB)')
    pci_slot = Field(int, 'Pci Slot')


# pylint: disable=too-many-instance-attributes
class MemoryDevice(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')
    bank_name = Field(str, 'Bank Name')
    size = Field(int, 'Size')
    status = Field(int, 'Status')
    manufacturer = Field(str, 'Manufacturer')
    part_number = Field(str, 'Part Number')
    serial_number = Field(str, 'Serial Number')
    type_details = Field(str, 'Type Details')
    manufacturer_date = Field(datetime.datetime, 'Manufacturer Date')
    speed = Field(int, 'Speed')
    current_operating_speed = Field(int, 'Current Operating Speed')
    rank = Field(str, 'Rank')
    instance_id = Field(str, 'Instance ID')
    device_description = Field(str, 'Device Description')


class PowerState(SmartJsonClass):
    id = Field(int, 'ID')
    power_state = Field(int, 'Power State')


class DeviceLicense(SmartJsonClass):
    sold_date = Field(datetime.datetime, 'Sold Date')
    license_bound = Field(int, 'Bound')
    eval_time_remaining = Field(int, 'Eval Time Remaining')
    assigned_devices = Field(str, 'Assigned Devices')
    license_status = Field(int, 'Status')
    entitlement_id = Field(str, 'Entitlement ID')
    license_description = Field(str, 'Description')
    license_type_name = Field(str, 'License Type Name')
    license_type_id = Field(int, 'License Type ID')


class DeviceCapability(SmartJsonClass):
    id = Field(int, 'ID')
    capability_id = Field(int, 'Capability ID')
    capability_name = Field(str, 'Capability Name')
    capability_description = Field(str, 'Capability Description')


class DeviceFru(SmartJsonClass):
    id = Field(int, 'ID')
    manufacturer = Field(str, 'Manufacturer')
    name = Field(str, 'Name')
    part_number = Field(str, 'PartNumber')
    serial_number = Field(str, 'SerialNumber')


class DeviceLocation(SmartJsonClass):
    id = Field(int, 'ID')
    rack = Field(str, 'Rack')
    aisle = Field(str, 'Aisle')
    data_center = Field(str, 'Data Center')


class DeviceSoftware(SmartJsonClass):
    version = Field(str, 'Version')
    installation_date = Field(datetime.datetime, 'Installation Date')
    status = Field(str, 'Status')
    software_type = Field(str, 'Software Type')
    component_id = Field(str, 'Component ID')
    device_description = Field(str, 'Description')
    instance_id = Field(str, 'Instance ID')


class SubSystemRollupStatus(SmartJsonClass):
    id = Field(int, 'ID')
    status = Field(int, 'Status')
    name = Field(str, 'Name')


class DellOmeDeviceInstance(DeviceAdapter):
    device_type = Field(int, 'Type')
    identifier = Field(str, 'Identifier')
    chassis_service_tag = Field(str, 'Chassis Service Tag')
    state = Field(int, 'State')
    managed_state = Field(int, 'Managed State')
    status = Field(int, 'Status')
    connection_status = Field(bool, 'Connection Status')
    asset_tag = Field(str, 'Asset Tag')
    system_id = Field(int, 'System ID')
    capabilities = ListField(int, 'Capabilities')
    server_cards = ListField(ServerCard, 'Server Cards')
    server_processors = ListField(ServerProcessor, 'Server Processors')
    server_host_names = ListField(HostName, 'Host Names')
    server_array_disks = ListField(ArrayDisk, 'Array Disks')
    server_raid_controls = ListField(RaidControl, 'Raid Controls')
    server_memory_devices = ListField(MemoryDevice, 'Memory Devices')
    server_power_states = ListField(PowerState, 'Power States')
    device_licenses = ListField(DeviceLicense, 'Device Licenses')
    device_capabilities = ListField(DeviceCapability, 'Device Capabilities')
    device_fru = ListField(DeviceFru, 'Device Fru')
    device_location = ListField(DeviceLocation, 'Device Location')
    device_softwares = ListField(DeviceSoftware, 'Device Software')
    sub_system_rollup_status = ListField(SubSystemRollupStatus, 'Sub System Rollup Status')
