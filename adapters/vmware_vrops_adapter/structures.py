import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass

RESOURCE_STATUS_ENUM = ['NONE', 'ERROR', 'UNKNOWN', 'DOWN', 'DATA_RECEIVING', 'OLD_DATA_RECEIVING',
                        'NO_DATA_RECEIVING', 'NO_PARENT_MONITORING', 'COLLECTOR_DOWN']
RESOURCE_STATE_ENUM = ['STOPPED', 'STARTING', 'STARTED', 'STOPPING', 'UPDATING', 'FAILED', 'MAINTAINED',
                       'MAINTAINED_MANUAL', 'REMOVING', 'NOT_EXISTING', 'NONE', 'UNKNOWN']
BADGE_TYPE = ['ANOMALY', 'CAPACITY_REMAINING', 'COMPLIANCE', 'DENSITY', 'EFFICIENCY', 'FAULT', 'HEALTH', 'RISK',
              'STRESS', 'TIME_REMAINING', 'TIME_REMAINING_WHAT_IF', 'RECLAIMABLE_CAPACITY', 'WORKLOAD']
BADGE_COLOR = ['GREEN', 'YELLOW', 'ORANGE', 'RED', 'GREY']
ALERT_LEVEL = ['UNKNOWN', 'NONE', 'INFORMATION', 'WARNING', 'IMMEDIATE', 'CRITICAL', 'AUTO']
ALERT_STATUS = ['NEW', 'ACTIVE', 'UPDATED', 'CANCELED']
CONTROL_STATE = ['OPEN', 'ASSIGNED', 'SUSPENDED', 'SUPPRESSED']
RESOURCE_HEALTH = ['GREEN', 'YELLOW', 'ORANGE', 'RED', 'GREY']


class ResourceIdentifier(SmartJsonClass):
    name = Field(str, 'Name')
    data_type = Field(str, 'Data Type')
    is_part_of_uniqueness = Field(bool, 'Part Of Uniqueness')
    value = Field(str, 'Value')


class ResourceKey(SmartJsonClass):
    name = Field(str, 'Name')
    adapter_kind_key = Field(str, 'Adapter Kind Key')
    resource_kind_key = Field(str, 'Resource Kind Key')
    resource_identifiers = ListField(ResourceIdentifier, 'Resource Identifiers')


class GeoLocation(SmartJsonClass):
    latitude = Field(float, 'Latitude')
    longitude = Field(float, 'Longitude')


class ResourceStatusState(SmartJsonClass):
    adapter_instance_id = Field(str, 'Adapter Instance ID')
    resource_status = Field(str, 'Resource Status', enum=RESOURCE_STATUS_ENUM)
    resource_state = Field(str, 'Resource State', enum=RESOURCE_STATE_ENUM)
    status_message = Field(str, 'Status Message')


class Badge(SmartJsonClass):
    type = Field(str, 'Type',
                 enum=BADGE_TYPE)
    color = Field(str, 'Color', enum=BADGE_COLOR)
    score = Field(float, 'Score')


class Alert(SmartJsonClass):
    alert_id = Field(str, 'Alert ID')
    resource_id = Field(str, 'Resource ID')
    alert_level = Field(str, 'Alert Level', enum=ALERT_LEVEL)
    alert_type = Field(str, 'Alert Type')
    sub_type = Field(str, 'Sub Type')
    status = Field(str, 'Status', enum=ALERT_STATUS)
    start_time = Field(datetime.datetime, 'Start Time')
    cancel_time = Field(datetime.datetime, 'Cancel Time')
    update_time = Field(datetime.datetime, 'Update Time')
    suspend_until_time = Field(datetime.datetime, 'Suspend Until Time')
    control_state = Field(str, 'Control State', enum=CONTROL_STATE)
    stat_key = Field(str, 'Stat Key')
    owner_id = Field(str, 'Owner ID')
    owner_name = Field(str, 'Owner Name')
    alert_definition_id = Field(str, 'Alert Definition ID')
    alert_definition_name = Field(str, 'Alert Definition Name')
    alert_impact = Field(str, 'Alert Impact')


class VmwareVropsDeviceInstance(DeviceAdapter):
    resource_key = Field(ResourceKey, 'Resource Key')
    credential_instance_id = Field(str, 'Credential Instance ID')
    geo_location = Field(GeoLocation, 'Geo Location')
    resource_status_states = ListField(ResourceStatusState, 'Resource Status States')
    resource_health = Field(str, 'Resource Health', enum=RESOURCE_HEALTH)
    resource_health_value = Field(float, 'Resource Health Value')
    monitoring_interval = Field(int, 'Monitoring Interval')
    badges = ListField(Badge, 'Badges')
    alerts = ListField(Alert, 'Alerts')
    esx_id = Field(str, 'ESX ID')
