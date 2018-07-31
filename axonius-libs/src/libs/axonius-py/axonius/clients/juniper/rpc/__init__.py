#pylint: disable=W0401
from axonius.clients.juniper.rpc.rpc import *
from axonius.clients.juniper.rpc.basic_info import *


def parse_device(type_, raw_datas):
    if type_ not in PARSE_DEVICE_CALLBACKS:
        raise ValueError(f'Unknown type {type_}')

    return PARSE_DEVICE_CALLBACKS[type_](raw_datas)


PARSE_DEVICE_CALLBACKS = {
    'ARP Device': parse_arps,
    'FDB Device': parse_fdbs,
    'Juniper Device': parse_basic_info,
}
