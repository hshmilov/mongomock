import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass


class InventoryActivation(SmartJsonClass):
    key = Field(str, 'Key')
    status = Field(str, 'Status')


class InventoryAgent(SmartJsonClass):
    version = Field(str, 'Version')
    configurable_profile = Field(str, 'Configurable Version')
    activations = ListField(InventoryActivation, 'Activations')
    connected_from = Field(str, 'Connected From')
    last_activity = Field(datetime.datetime, 'Last Activity')
    last_checked_in = Field(datetime.datetime, 'Last Checked In')
    last_inventory = Field(datetime.datetime, 'Last Inventory')
    udc_manifest_assigned = Field(bool, 'UDC Manifest Assigned')


class InventorySensor(SmartJsonClass):
    activated_modules = ListField(str, 'Activated Modules')
    pending_activation_modules = ListField(str, 'Pending Activation For Modules')
    last_vm_scan = Field(datetime.datetime, 'Last VM Scan')
    last_compliance_scan = Field(datetime.datetime, 'Last Compliance Scan')
    last_full_scan = Field(datetime.datetime, 'Last Full Scan')
    error_status = Field(bool, 'Error Status')


class InventoryContainer(SmartJsonClass):
    product = Field(str, 'Product')
    version = Field(str, 'Version')
    num_of_container = Field(int, 'Number Of Containers')
    num_of_images = Field(int, 'Number Of Images')


class InventoryProcessor(SmartJsonClass):
    description = Field(str, 'Description')
    speed = Field(int, 'Speed')
    number_cpus = Field(int, 'Number Of CPUs')


class InventoryInstance(SmartJsonClass):
    host_id = Field(str, 'Host ID')
    agent_id = Field(str, 'Agent ID')
    create_date = Field(datetime.datetime, 'Create Date')
    sensor_last_update_date = Field(datetime.datetime, 'Sensor Last Update Date')
    asset_type = Field(str, 'Asset Type')
    most_frequent_user = Field(str, 'Most Frequent User')
    is_container_host = Field(bool, 'Is Container Host')
    is_hypervisor = Field(bool, 'Is Hypervisor')

    sensor = Field(InventorySensor, 'Sensor')
    container = Field(InventoryContainer, 'Container')
    inventory_agent = Field(InventoryAgent, 'Agent')
