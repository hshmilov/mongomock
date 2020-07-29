import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class LocalAdminMap(SmartJsonClass):
    domain = Field(str, 'Domain')
    domainandname = Field(str, 'Domain And Name')
    sidusage = Field(int, 'SID Usage')
    sid = Field(str, 'SID')
    user = Field(str, 'User')
    svc_acct = Field(bool, 'Service Account')
    on_host = Field(bool, 'On Host')
    inserted_ts = Field(datetime.datetime, 'Inserted Time')
    user_id = Field(str, 'User ID')
    expiring = Field(str, 'Expiring')
    active = Field(bool, 'Active')
    persistent = Field(bool, 'Persistent')


class ScanData(SmartJsonClass):
    msg = Field(str, 'Message')
    duration = Field(float, 'Duration')
    scan_time = Field(datetime.datetime, 'First Scanned')
    success = Field(bool, 'Is Success')
    error = Field(str, 'Error')


class RemediantSecureoneDeviceInstance(DeviceAdapter):
    last_scanned = Field(datetime.datetime, 'Most Recent Scan')
    local_admins_map = ListField(LocalAdminMap, 'Local Admins Mapping')
    secure_policy = Field(bool, 'Protect Mode Enabled')
    scan_policy = Field(bool, 'Scan Mode Enabled')
    manage_local_sids_policy = Field(bool, 'Offline Access Management Enabled')
    strict_secure_policy = Field(bool, 'Deny New Accounts Enabled')
    last_scan_attempt = Field(ScanData, 'Last Scan Attempt Data')
