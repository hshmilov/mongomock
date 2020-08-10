import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class IbmQradarLogSourceTypeInstance(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')
    internal = Field(bool, 'Internal')
    custom = Field(bool, 'Custom')
    version = Field(str, 'Version')


class IbmQradarLogSourceGroupInstance(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')
    description = Field(str, 'Description')
    parent_id = Field(int, 'Parent ID')
    owner = Field(str, 'Owner')
    last_modified = Field(datetime.datetime, 'Last Modified')


class IbmQradarLogSourceStatus(SmartJsonClass):
    severity = Field(str, 'Severity')
    text = Field(str, 'Text')
    timestamp = Field(datetime.datetime, 'Timestamp')


class IbmQradarDeviceInstance(DeviceAdapter):
    protocol_type = Field(int, 'Protocol Type ID')
    gateway = Field(bool, 'Is Gateway')
    internal = Field(bool, 'Is Internal')
    credibility = Field(int, 'Credibility')
    event_collector_id = Field(int, 'Even Collector ID')
    extension_id = Field(int, 'Extension ID')
    language_id = Field(int, 'Language ID')
    groups_ids = ListField(int, 'Group IDs')
    status = Field(str, 'Status')
    auto_discovered = Field(bool, 'Auto Discovered')
    log_source_statuses = ListField(IbmQradarLogSourceStatus, 'Log Source Statuses')
    log_source_type = Field(IbmQradarLogSourceTypeInstance, 'Log Source Type')
    log_source_groups = ListField(IbmQradarLogSourceGroupInstance, 'Log Source Groups')
