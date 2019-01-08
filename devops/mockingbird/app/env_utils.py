import importlib
import struct
import socket

from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter


def ip2int(addr):
    return struct.unpack('!I', socket.inet_aton(addr))[0]


def int2ip(addr):
    return socket.inet_ntoa(struct.pack('!I', addr))


def create_my_device_adapter(adapter_name: str) -> DeviceAdapter:
    module = importlib.import_module(f'{adapter_name}_adapter.service')
    adapter_class = getattr(module, ''.join(
        [word.capitalize() for word in adapter_name.replace('_', ' ').replace('-', ' ').split(' ')]) + 'Adapter')
    return adapter_class.MyDeviceAdapter(set(), set())


def create_my_user_adapter(adapter_name: str) -> UserAdapter:
    module = importlib.import_module(f'{adapter_name}_adapter.service')
    adapter_class = getattr(module, ''.join(
        [word.capitalize() for word in adapter_name.replace('_', ' ').replace('-', ' ').split(' ')]) + 'Adapter')
    return adapter_class.MyUserAdapter(set(), set())
