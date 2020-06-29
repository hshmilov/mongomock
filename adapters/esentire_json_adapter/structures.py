from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter


class EsentireJsonDeviceInstance(DeviceAdapter):
    sensor = Field(str, 'Sensor')
    network_tap = Field(str, 'Network Tap')
    total_traffic_in_bytes = Field(int, 'Total Traffic (Bytes)')
    parsed_hostnames = ListField(str, 'Host names')
