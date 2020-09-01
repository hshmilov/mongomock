from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class NasuniAlertSettings(SmartJsonClass):
    enabled = Field(bool, 'Alerts Enabled')
    threshold = Field(int, 'Usage Threshold')
    duration = Field(int, 'Duration Threshold')


class Cache(SmartJsonClass):
    reserved = Field(str, 'Reserved')
    cache_max = Field(int, 'Maximum')
    cache_min = Field(int, 'Minimum')


class RemoteSupport(SmartJsonClass):
    connected = Field(bool, 'Connected')
    enabled = Field(bool, 'Enabled')
    running = Field(bool, 'Running')
    timeout = Field(int, 'Timeout')


class Updates(SmartJsonClass):
    available = Field(bool, 'Available')
    current_version = Field(str, 'Current Version')
    new_version = Field(str, 'New Version')


class SNMP(SmartJsonClass):
    v2_enabled = Field(bool, 'V2 Enabled')
    v2_community = Field(str, 'V2 Community')
    v3_enabled = Field(bool, 'V3 Enabled')
    v3_username = Field(str, 'V3 Username')
    sys_location = Field(str, 'Sys Location')
    sys_contact = Field(str, 'Sys Contact')
    trap_ips = ListField(str, 'Trap IPs')


class CIFS(SmartJsonClass):
    aio_support = Field(bool, 'Async IO Support')
    deny_access = Field(bool, 'Deny Access')
    fruit_support = Field(bool, 'Available Mac OS Extensions')
    proto_level = Field(str, 'Protocol Level')
    restrict_anonymous = Field(bool, 'Restrict Anonymous')
    roundup_size = Field(str, 'Allocation Roundup Size')
    smb3 = Field(bool, 'SMB3')
    smb3_encrypt = Field(bool, 'SMB3 Encrypt')


class NasuniDeviceInstance(DeviceAdapter):
    version = Field(str, 'Version')
    management_state = Field(str, 'Management State')
    cpu_alert_settings = Field(NasuniAlertSettings, 'CPU Usage Alert Settings')
    memory_alert_settings = Field(NasuniAlertSettings, 'Memory Usage Alert Settings')
    snap_shot_alert_settings = Field(NasuniAlertSettings, 'Snapshot Usage Alert Settings')
    cache_reserved = Field(Cache, 'Cache Reserved')
    remote_support = Field(RemoteSupport, 'Remote Support')
    snmp = Field(SNMP, 'SNMP')
    updates = Field(Updates, 'Updates')
    cifs = Field(CIFS, 'CIFS')
