import logging
import socket

from axonius.devices.device_adapter import DeviceAdapterNetworkInterface

logger = logging.getLogger(f'axonius.{__name__}')


def unpack_mac(value):
    return ('%02X:' * 6)[:-1] % tuple(map(ord, str(value)))


def extract_ip_from_mib(mib):
    return '.'.join(str(mib).split('.')[-4:])


# parsers for the SnmpTable

def parse_unhandled(oid, value):
    # this function is a callback so it must have the same api as the above functions
    logger.debug(f'Unhandled oid: {oid} value: {value}')


def parse_admin(oid, value):
    admin_enum = [x for x in DeviceAdapterNetworkInterface.fields_info if x == 'admin_status'][0].enum

    value = int(value) - 1

    if value not in range(len(admin_enum)):
        raise ValueError(f'Invalid value {value}')

    return admin_enum[value]


def parse_operational(oid, value):
    operational_enum = \
        [x for x in DeviceAdapterNetworkInterface.fields_info if x == 'operational_status'][0].enum

    value = int(value) - 1

    if value not in range(len(operational_enum)):
        raise ValueError(f'Invalid value {value + 1}')

    return operational_enum[value]


def parse_ip(oid, value):
    # this function is a callback so it must have the same api as the above functions
    return socket.inet_ntoa(bytes(value))


def parse_mac(oid, value):
    # this function is a callback so it must have the same api as the above functions
    return unpack_mac(value)


def parse_str(oid, value):
    # this function is a callback so it must have the same api as the above functions
    return str(value)


class SnmpTable:
    """ Abstract class for oid, value parsing given table and index """
    table = {}
    index = 0

    @classmethod
    def parse_value(cls, oid, value):
        parser, name = cls.table.get(oid[cls.index], (parse_unhandled, 'unhandled'))

        # skip empty
        if str(value) == '':
            logger.warning(f'Skipping empty value for {name} {oid} {value}')
            return (None, None)

        value = parser(oid, value)
        return (name, value)
