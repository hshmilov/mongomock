import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter


class AwakeDeviceInstance(DeviceAdapter):
    duration = Field(str, 'Duration')
    device_type = Field(str, 'Device Type')
    monitoring_point_ids = ListField(int, 'Montiroing Point Ids')
    application = ListField(str, 'Applications')
    notability_percentile = Field(int, 'Notability Percentile')
    number_similar_devices = Field(int, 'Number Similar Devices')
    number_sessions = Field(int, 'Number Sessions')
    white_listed = Field(bool, 'White Listed')
    ack_time = Field(datetime.datetime, 'Ack Time')
