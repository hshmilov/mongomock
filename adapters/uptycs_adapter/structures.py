import datetime

from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class UptycsDeviceInstance(DeviceAdapter):
    location = Field(str, 'Location')
    device_status = Field(str, 'Device Status')
    os_query_version = Field(str, 'osQuery Version')
    uptated_by = Field(str, 'Updated By')
    last_enrolled_at = Field(datetime.datetime, 'Last Enrolled At')
    deleted_at = Field(datetime.datetime, 'Deleted At')
    config_id = Field(str, 'Config ID')
    live = Field(bool, 'Live')
