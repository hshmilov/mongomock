from axonius.fields import Field, JsonStringFormat, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import format_ip, format_ip_raw


class LimacharlieDeviceInstance(DeviceAdapter):
    sid = Field(str, 'Sensor ID')
    is_online = Field(bool, 'Is Online')
    is_isolated = Field(bool, 'Is Isolated')
    should_isolate = Field(bool, 'Should Isolate')
    is_kernel_available = Field(bool, 'Is Kernel Available')
    external_ip = Field(str, 'External IP', converter=format_ip, json_format=JsonStringFormat.ip)
    external_ip_raw = ListField(str, converter=format_ip_raw, hidden=True)
