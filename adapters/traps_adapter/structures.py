import datetime

from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class TrapsDeviceInstance(DeviceAdapter):
    cyvera_version = Field(str, 'Cyvera Version')
    content_version = Field(str, 'Content Version')
    heartbeat_interval_minutes = Field(int, 'Heartbeat Interval Minutes')
    is_64 = Field(bool, 'Is 64 bit')
    is_os_compatible = Field(bool, 'Is Os Compatible')
    last_data_update_time = Field(datetime.datetime, 'Last Data Update Time')
    last_heartbeat_time = Field(datetime.datetime, 'Last Heartbeat Time')
    license_expiration_date = Field(datetime.datetime, 'License Expiration Date')
    is_on = Field(bool, 'Is On')
