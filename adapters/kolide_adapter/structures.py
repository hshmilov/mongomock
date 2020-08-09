from datetime import datetime

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field


class KolideDeviceInstance(DeviceAdapter):
    osquery_version = Field(str, 'Osquery Version')
    status = Field(str, 'Status')
    updated_at = Field(datetime, 'Updated At')
    detail_update_time = Field(datetime, 'Detail Update Time')
    created_at = Field(datetime, 'Created At')
    platform = Field(str, 'Platform')
