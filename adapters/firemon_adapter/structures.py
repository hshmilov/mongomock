import datetime

from axonius.fields import Field, JsonStringFormat
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import format_ip


class FiremonDeviceInstance(DeviceAdapter):
    device_type = Field(str, 'Device Type')
    management_ip = Field(str, 'Management IP', converter=format_ip, json_format=JsonStringFormat.ip)
    last_updated = Field(datetime.datetime, 'Last Updated')
    last_revision = Field(datetime.datetime, 'Last Revision')
