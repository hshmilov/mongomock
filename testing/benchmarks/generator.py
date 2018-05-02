import random
import datetime
import ipaddress
import netaddr

from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD, MAC_FIELD, IPS_FIELD


def generate_correlated_by_ip_mac(key):
    """
    :param key: a number used to create a device dict. Devices created with the same number should correlate
    :return:
    """
    return {
        "_id": str(random.getrandbits(256)),
        "internal_axon_id": str(random.getrandbits(256)),
        "accurate_for_datetime": datetime.datetime.now().isoformat(),
        "adapters": [
            {
                "client_used": "10.0.2.119:22",
                "plugin_type": "Adapter",
                "plugin_name": "cisco_adapter",
                "plugin_unique_name": "cisco_adapter_42687",
                "accurate_for_datetime": datetime.datetime.now().isoformat(),
                "data": {
                    "id": str(random.getrandbits(256)),
                    NETWORK_INTERFACES_FIELD: [
                        {
                            IPS_FIELD: [
                                "10.0.2.1", str(ipaddress.ip_address(key % 0xffffffff))
                            ],
                            MAC_FIELD: str(netaddr.EUI(key))
                        }
                    ]
                }
            }
        ],
        "tags": []
    }
