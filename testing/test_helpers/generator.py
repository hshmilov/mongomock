import random
import datetime
import ipaddress
import netaddr

from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD, MAC_FIELD, IPS_FIELD
from axonius.utils.hash import get_preferred_quick_adapter_id


def generate_correlated_by_ip_mac(key):
    """
    :param key: a number used to create a device dict. Devices created with the same number should correlate
    :return:
    """
    _id = str(random.getrandbits(256))
    pun = 'cisco_adapter_42687'
    return {
        '_id': str(random.getrandbits(256)),
        'internal_axon_id': str(random.getrandbits(256)),
        'accurate_for_datetime': datetime.datetime.now().isoformat(),
        'adapters': [
            {
                'client_used': '10.0.2.119:22',
                'plugin_type': 'Adapter',
                'plugin_name': 'cisco_adapter',
                'plugin_unique_name': pun,
                'accurate_for_datetime': datetime.datetime.now().isoformat(),
                'quick_id': get_preferred_quick_adapter_id(pun, _id),
                'data': {
                    'id': _id,
                    NETWORK_INTERFACES_FIELD: [
                        {
                            IPS_FIELD: [
                                '10.0.2.1', str(ipaddress.ip_address(key % 0xffffffff))
                            ],
                            MAC_FIELD: str(netaddr.EUI(key))
                        }
                    ]
                }
            }
        ],
        'tags': []
    }


def generate_correlated_serial(key):
    """
    :param key: a number used to create a device dict. Devices created with the same number should correlate
    :return:
    """
    _id = str(random.getrandbits(256))
    pun = 'cisco_adapter_42687'
    return {
        '_id': str(random.getrandbits(256)),
        'internal_axon_id': str(random.getrandbits(256)),
        'accurate_for_datetime': datetime.datetime.now().isoformat(),
        'adapters': [
            {
                'client_used': '10.0.2.119:22',
                'plugin_type': 'Adapter',
                'plugin_name': 'cisco_adapter',
                'plugin_unique_name': pun,
                'accurate_for_datetime': datetime.datetime.now().isoformat(),
                'quick_id': get_preferred_quick_adapter_id(pun, _id),
                'data': {
                    'id': _id,
                    'device_serial': str(key)
                }
            }
        ],
        'tags': []
    }


def generate_correlated_hostname_ip(key):
    """
    :param key: a number used to create a device dict. Devices created with the same number should correlate
    :return:
    """
    _id = str(random.getrandbits(256))
    pun = 'cisco_adapter_42687'
    return {
        '_id': str(random.getrandbits(256)),
        'internal_axon_id': str(random.getrandbits(256)),
        'accurate_for_datetime': datetime.datetime.now().isoformat(),
        'adapters': [
            {
                'client_used': '10.0.2.119:22',
                'plugin_type': 'Adapter',
                'plugin_name': 'cisco_adapter',
                'plugin_unique_name': pun,
                'accurate_for_datetime': datetime.datetime.now().isoformat(),
                'quick_id': get_preferred_quick_adapter_id(pun, _id),
                'data': {
                    'id': _id,
                    'hostname': str(key),
                    NETWORK_INTERFACES_FIELD: [
                        {
                            IPS_FIELD: [
                                '10.0.2.1', str(ipaddress.ip_address(key % 0xffffffff))
                            ],
                            MAC_FIELD: str(netaddr.EUI(key))
                        }
                    ]
                }
            }
        ],
        'tags': []
    }
