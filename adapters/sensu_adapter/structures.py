from axonius.fields import ListField
from axonius.devices.device_adapter import DeviceAdapter


class SensuDeviceInstance(DeviceAdapter):
    subscriptions = ListField(str, 'Subscriptions')
