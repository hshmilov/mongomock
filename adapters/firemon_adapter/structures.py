import datetime

from axonius.fields import Field, ListField, JsonStringFormat
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import format_ip, format_ip_raw


class FiremonDeviceInstance(DeviceAdapter):
    device_type = Field(str, 'Device Type')
    management_ip = Field(str, 'Management IP', converter=format_ip, json_format=JsonStringFormat.ip)
    management_ip_raw = ListField(str, converter=format_ip_raw, hidden=True)
    last_updated = Field(datetime.datetime, 'Last Updated')
    last_revision = Field(datetime.datetime, 'Last Revision')
