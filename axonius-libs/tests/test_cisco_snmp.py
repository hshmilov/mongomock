# pylint: disable=wildcard-import,too-many-lines,line-too-long

import datetime
import os
import pickle

import pytest

from axonius.clients.cisco.abstract import CiscoDevice
from axonius.clients.cisco.snmp import *
from axonius.clients.cisco.snmp import SnmpArpCiscoData

CISCO_ARP_PICKLE = 'cisco_arp.pkl'
CISCO_CDP_PICKLE = 'cisco_cdp.pkl'
CISCO_BASIC_PICKLE = 'cisco_basic.pkl'

IP_FIELD = get_oid_name(OIDS.ip)
IFACE_FIELD = get_oid_name(OIDS.interface)
PORT_SECURITY_FIELD = get_oid_name(OIDS.port_security)


def create_device():
    return CiscoDevice(set(), set())


def file_relative(path):
    return os.path.join(os.path.dirname(__file__), path)


def dump_pickles():
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO)
    client = CiscoSnmpClient(host='cisco-switch', community='public', port=161)
    client.validate_connection()
    results = list(client.query_all())

    arp = list(filter(lambda x: isinstance(x, SnmpArpCiscoData), results))[0]
    basic = list(filter(lambda x: isinstance(x, SnmpBasicInfoCiscoData), results))[0]

    basic.get_parsed_data()

    with open(file_relative(CISCO_ARP_PICKLE), 'wb') as f:
        f.write(pickle.dumps(arp))

    with open(file_relative(CISCO_BASIC_PICKLE), 'wb') as f:
        f.write(pickle.dumps(basic))


def get_mock(path):
    fullpath = file_relative(path)
    with open(fullpath, 'rb') as file_:
        return pickle.loads(file_.read())


def get_cdp_mock():
    return get_mock(CISCO_CDP_PICKLE)


def get_arp_mock():
    return get_mock(CISCO_ARP_PICKLE)


def get_basic_info_mock():
    return get_mock(CISCO_BASIC_PICKLE)


# pylint: disable=redefined-outer-name
@pytest.fixture(scope='session')
def mocks():
    Mocks = namedtuple('mocks', ('arp', 'cdp', 'basic'))
    return Mocks(arp=get_arp_mock(), cdp=get_cdp_mock(), basic=get_basic_info_mock())


def test_cdp_data(mocks):
    cdp = mocks.cdp
    parsed_data = cdp.get_parsed_data()
    assert parsed_data == [
        {
            'ip': '192.168.2.3',
            'version': 'Cisco IOS Software, C2960S Software (C2960S-UNIVERSALK9-M), Version 15.2(2a)E1, RELEASE SOFTWARE (fc1)\nTechnical Support: http://www.cisco.com/techsupport\nCopyright (c) 1986-2014 by Cisco Systems, Inc.\nCompiled Wed 10-Dec-14 03:54 by prod_rel_team',
            'hostname': 'MAG.mag-stack.praxis.local',
            'iface': 'GigabitEthernet2/0/42',
            'device_model': 'cisco WS-C2960S-F48FPS-L',
            'connected_devices': [{'name': '194.1.146.0', 'iface': '', 'type': 'Direct'}],
        },
        {
            'ip': '192.168.2.3',
            'version': 'Cisco IOS Software, C2960S Software (C2960S-UNIVERSALK9-M), Version 15.2(2a)E1, RELEASE SOFTWARE (fc1)\nTechnical Support: http://www.cisco.com/techsupport\nCopyright (c) 1986-2014 by Cisco Systems, Inc.\nCompiled Wed 10-Dec-14 03:54 by prod_rel_team',
            'hostname': 'MAG.mag-stack.praxis.local',
            'iface': 'GigabitEthernet3/0/46',
            'device_model': 'cisco WS-C2960S-F48FPS-L',
            'connected_devices': [{'name': '194.1.146.0', 'iface': '', 'type': 'Direct'}],
        },
        {
            'ip': '192.168.3.3',
            'version': 'Cisco IOS Software, C2960S Software (C2960S-UNIVERSALK9-M), Version 15.2(2a)E1, RELEASE SOFTWARE (fc1)\nTechnical Support: http://www.cisco.com/techsupport\nCopyright (c) 1986-2014 by Cisco Systems, Inc.\nCompiled Wed 10-Dec-14 03:54 by prod_rel_team',
            'hostname': 'MAG.mag-stack.praxis.local',
            'iface': 'GigabitEthernet2/0/47',
            'device_model': 'cisco WS-C2960S-F48FPS-L',
            'connected_devices': [{'name': '194.1.146.0', 'iface': '', 'type': 'Direct'}],
        },
    ]
    devices = list(cdp.get_devices(create_device))
    assert len(devices) == 3
    assert devices[0].to_dict() == {
        'adapter_properties': ['Network'],
        'connected_devices': [{'connection_type': 'Direct', 'remote_name': '194.1.146.0'}],
        'device_model': 'cisco WS-C2960S-F48FPS-L',
        'fetch_proto': 'CDP',
        'hostname': 'MAG.mag-stack.praxis.local',
        'id': 'cdp_MAG.mag-stack.praxis.local',
        'network_interfaces': [{'ips': ['192.168.2.3'], 'ips_raw': [3_232_236_035], 'name': 'GigabitEthernet2/0/42'}],
        'os': {
            'build': 'Cisco IOS Software, C2960S Software (C2960S-UNIVERSALK9-M), '
                     + 'Version 15.2(2a)E1, RELEASE SOFTWARE (fc1)\n'
                     + 'Technical Support: http://www.cisco.com/techsupport\n'
                     + 'Copyright (c) 1986-2014 by Cisco Systems, Inc.\n'
                     + 'Compiled Wed 10-Dec-14 03:54 by prod_rel_team',
            'type': 'Cisco',
        },
        'raw': {
            'connected_devices': [{'iface': '', 'name': '194.1.146.0', 'type': 'Direct'}],
            'device_model': 'cisco WS-C2960S-F48FPS-L',
            'hostname': 'MAG.mag-stack.praxis.local',
            'iface': 'GigabitEthernet2/0/42',
            'ip': '192.168.2.3',
            'version': 'Cisco IOS Software, C2960S Software '
                       + '(C2960S-UNIVERSALK9-M), Version 15.2(2a)E1, RELEASE '
                       + 'SOFTWARE (fc1)\n'
                       + 'Technical Support: http://www.cisco.com/techsupport\n'
                       + 'Copyright (c) 1986-2014 by Cisco Systems, Inc.\n'
                       + 'Compiled Wed 10-Dec-14 03:54 by prod_rel_team',
        },
    }


def test_arp_data(mocks):
    arp = mocks.arp
    parsed_data = arp.get_parsed_data()
    assert parsed_data == [
        {
            'mac': '90:6C:AC:FE:5B:BC',
            'ip': '192.168.10.1',
            'connected_devices': [{'name': 'cisco-switch', 'iface': '', 'type': 'Indirect'}],
        },
        {
            'mac': '00:1B:8F:DF:DF:40',
            'ip': '192.168.10.6',
            'connected_devices': [{'name': 'cisco-switch', 'iface': '', 'type': 'Indirect'}],
        },
        {
            'mac': '00:23:24:F1:0D:FA',
            'ip': '192.168.10.27',
            'connected_devices': [{'name': 'cisco-switch', 'iface': '', 'type': 'Indirect'}],
        },
        {
            'mac': '00:90:0B:4E:83:22',
            'ip': '192.168.10.249',
            'connected_devices': [{'name': 'cisco-switch', 'iface': '', 'type': 'Indirect'}],
        },
    ]
    devices = list(arp.get_devices(create_device))
    assert len(devices) == 4
    assert devices[0].to_dict() == {
        'id': 'arp_90:6C:AC:FE:5B:BC',
        'network_interfaces': [
            {
                'mac': '90:6C:AC:FE:5B:BC',
                'manufacturer': 'Fortinet, Inc. (899 Kifer Road Sunnyvale California US 94086 )',
                'ips': ['192.168.10.1'],
                'ips_raw': [3_232_238_081],
            }
        ],
        'connected_devices': [{'remote_name': 'cisco-switch', 'connection_type': 'Indirect'}],
        'os': {},
        'raw': {
            'mac': '90:6C:AC:FE:5B:BC',
            'ip': '192.168.10.1',
            'connected_devices': [{'name': 'cisco-switch', 'iface': '', 'type': 'Indirect'}],
        },
        'fetch_proto': 'ARP',
        'adapter_properties': ['Network'],
    }


# pylint: disable=line-too-long
def test_basic_info_parsed_data(mocks):
    basic = mocks.basic
    parsed_data = basic.get_parsed_data()
    if 'uptime' in parsed_data[0]:
        parsed_data[0]['uptime'] = '301177616'

    assert parsed_data == [
        {
            'os': 'cisco',
            'version': 'Cisco IOS Software, C2960 Software (C2960-LANBASEK9-M), Version 12.2(55)SE10, RELEASE SOFTWARE (fc2)\r\nTechnical Support: http://www.cisco.com/techsupport\r\nCopyright (c) 1986-2015 by Cisco Systems, Inc.\r\nCompiled Wed 11-Feb-15 11:46 by prod_rel_team',
            'uptime': '301177616',
            'hostname': 'cisco-switch.axonius.lan',
            IFACE_FIELD: {
                '1': {
                    'index': '1',
                    'description': 'Vlan1',
                    'type': '53',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:40',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    'ip': [
                        {
                            'address': '192.168.10.6',
                            'index': '1',
                            'net-mask': '255.255.255.0'
                        }
                    ]
                },
                '10101': {
                    'index': '10101',
                    'description': 'GigabitEthernet0/1',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:01',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10102': {
                    'index': '10102',
                    'description': 'GigabitEthernet0/2',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:02',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10103': {
                    'index': '10103',
                    'description': 'GigabitEthernet0/3',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:03',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10104': {
                    'index': '10104',
                    'description': 'GigabitEthernet0/4',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:04',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10105': {
                    'index': '10105',
                    'description': 'GigabitEthernet0/5',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:05',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10106': {
                    'index': '10106',
                    'description': 'GigabitEthernet0/6',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:06',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10107': {
                    'index': '10107',
                    'description': 'GigabitEthernet0/7',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:07',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10108': {
                    'index': '10108',
                    'description': 'GigabitEthernet0/8',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:08',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10109': {
                    'index': '10109',
                    'description': 'GigabitEthernet0/9',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:09',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10110': {
                    'index': '10110',
                    'description': 'GigabitEthernet0/10',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:0A',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10111': {
                    'index': '10111',
                    'description': 'GigabitEthernet0/11',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:0B',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10112': {
                    'index': '10112',
                    'description': 'GigabitEthernet0/12',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:0C',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10113': {
                    'index': '10113',
                    'description': 'GigabitEthernet0/13',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:0D',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10114': {
                    'index': '10114',
                    'description': 'GigabitEthernet0/14',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:0E',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10115': {
                    'index': '10115',
                    'description': 'GigabitEthernet0/15',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:0F',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10116': {
                    'index': '10116',
                    'description': 'GigabitEthernet0/16',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:10',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10117': {
                    'index': '10117',
                    'description': 'GigabitEthernet0/17',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:11',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10118': {
                    'index': '10118',
                    'description': 'GigabitEthernet0/18',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:12',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10119': {
                    'index': '10119',
                    'description': 'GigabitEthernet0/19',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:13',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10120': {
                    'index': '10120',
                    'description': 'GigabitEthernet0/20',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:14',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10121': {
                    'index': '10121',
                    'description': 'GigabitEthernet0/21',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:15',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10122': {
                    'index': '10122',
                    'description': 'GigabitEthernet0/22',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:16',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10123': {
                    'index': '10123',
                    'description': 'GigabitEthernet0/23',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:17',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10124': {
                    'index': '10124',
                    'description': 'GigabitEthernet0/24',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:18',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10125': {
                    'index': '10125',
                    'description': 'GigabitEthernet0/25',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:19',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10126': {
                    'index': '10126',
                    'description': 'GigabitEthernet0/26',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:1A',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10127': {
                    'index': '10127',
                    'description': 'GigabitEthernet0/27',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:1B',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10128': {
                    'index': '10128',
                    'description': 'GigabitEthernet0/28',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:1C',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10129': {
                    'index': '10129',
                    'description': 'GigabitEthernet0/29',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:1D',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10130': {
                    'index': '10130',
                    'description': 'GigabitEthernet0/30',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:1E',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10131': {
                    'index': '10131',
                    'description': 'GigabitEthernet0/31',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:1F',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10132': {
                    'index': '10132',
                    'description': 'GigabitEthernet0/32',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:20',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10133': {
                    'index': '10133',
                    'description': 'GigabitEthernet0/33',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '100000000',
                    'mac': '00:1B:8F:DF:DF:21',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10134': {
                    'index': '10134',
                    'description': 'GigabitEthernet0/34',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:22',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10135': {
                    'index': '10135',
                    'description': 'GigabitEthernet0/35',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:23',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10136': {
                    'index': '10136',
                    'description': 'GigabitEthernet0/36',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:24',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10137': {
                    'index': '10137',
                    'description': 'GigabitEthernet0/37',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:25',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10138': {
                    'index': '10138',
                    'description': 'GigabitEthernet0/38',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:26',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10139': {
                    'index': '10139',
                    'description': 'GigabitEthernet0/39',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:27',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10140': {
                    'index': '10140',
                    'description': 'GigabitEthernet0/40',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:28',
                    'admin-status': 'Down',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': True,
                        'status': 'securedown',
                        'max_addr': 5,
                        'violation_action': 'dropNotify',
                        'violation_count': 0,
                        'sticky': False,
                        'entries': {
                            '34:75:C7:E9:62:11': {
                                'type': 'Dynamic',
                                'vlan_id': '1',
                                'remaining_age': 0
                            },
                            '34:75:C7:E9:67:22': {
                                'type': 'Dynamic',
                                'vlan_id': '1',
                                'remaining_age': 0
                            }
                        }
                    },
                    'port_access': {
                        'port_mode': 1,
                        'guest_vlan_number': 0,
                        'auth_fail_vlan_number': 0,
                        'operation_vlan_number': 0,
                        'operation_vlan_type': 2,
                        'auth_fail_max_attempts': 3
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10141': {
                    'index': '10141',
                    'description': 'GigabitEthernet0/41',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:29',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    PORT_SECURITY_FIELD: {
                        'enabled': True,
                        'status': 'secureup',
                        'max_addr': 10,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': True,
                        'entries': {
                            '00:0C:6C:0A:4A:AA': {
                                'type': 'Sticky',
                                'vlan_id': '12',
                                'remaining_age': 0
                            },
                            '00:0C:6C:0A:4E:EB': {
                                'type': 'Sticky',
                                'vlan_id': '12',
                                'remaining_age': 0
                            },
                            '00:50:B6:87:92:98': {
                                'type': 'Sticky',
                                'vlan_id': '12',
                                'remaining_age': 0
                            },
                            '34:75:A7:E9:A8:C9': {
                                'type': 'Sticky',
                                'vlan_id': '99',
                                'remaining_age': 0
                            },
                            '34:75:C7:E9:88:88': {
                                'type': 'Sticky',
                                'vlan_id': '99',
                                'remaining_age': 0
                            },
                            '34:75:C7:E9:A8:C9': {
                                'type': 'Dynamic',
                                'vlan_id': '99',
                                'remaining_age': 0
                            }
                        }
                    },
                    'port_access': {
                        'port_mode': 1,
                        'guest_vlan_number': 0,
                        'auth_fail_vlan_number': 0,
                        'operation_vlan_number': 0,
                        'operation_vlan_type': 2,
                        'auth_fail_max_attempts': 3
                    },
                    'vlans': {
                        'voice_vlan': {
                            'vlan_id': 99,
                            'vlan_name': 'VLAN0099'
                        }
                    }
                },
                '10142': {
                    'index': '10142',
                    'description': 'GigabitEthernet0/42',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:2A',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10143': {
                    'index': '10143',
                    'description': 'GigabitEthernet0/43',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:2B',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10144': {
                    'index': '10144',
                    'description': 'GigabitEthernet0/44',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:2C',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10145': {
                    'index': '10145',
                    'description': 'GigabitEthernet0/45',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:2D',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10146': {
                    'index': '10146',
                    'description': 'GigabitEthernet0/46',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:2E',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10147': {
                    'index': '10147',
                    'description': 'GigabitEthernet0/47',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '10000000',
                    'mac': '00:1B:8F:DF:DF:2F',
                    'admin-status': 'Up',
                    'operation-status': 'Down',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10148': {
                    'index': '10148',
                    'description': 'GigabitEthernet0/48',
                    'type': '6',
                    'mtu': '1500',
                    'speed': '1000000000',
                    'mac': '00:1B:8F:DF:DF:30',
                    'admin-status': 'Up',
                    'operation-status': 'Up',
                    PORT_SECURITY_FIELD: {
                        'enabled': False,
                        'status': 'securedown',
                        'max_addr': 1,
                        'violation_action': 'shutdown',
                        'violation_count': 0,
                        'sticky': False
                    },
                    'vlans': {
                        'vlan': {
                            'vlan_id': [
                                1
                            ],
                            'vlan_name': [
                                'default'
                            ]
                        }
                    }
                },
                '10501': {
                    'index': '10501',
                    'description': 'Null0',
                    'type': '1',
                    'mtu': '1500',
                    'speed': '4294967295',
                    'admin-status': 'Up',
                    'operation-status': 'Up'
                }
            },
            'device_model': 'WS-C2960G-48TC-L',
            'device_serial': 'FOC1115Z2Y5',
            'vtp_vlans': {
                '1': 'default',
                '10': 'VLAN0010',
                '12': 'VLAN0012',
                '14': 'VLAN0014',
                '78': 'VLAN0078',
                '99': 'VLAN0099',
                '1002': 'fddi-default',
                '1003': 'token-ring-default',
                '1004': 'fddinet-default',
                '1005': 'trnet-default'
            }
        }
    ]

    def test_basic_info_devices(mocks):
        basic = mocks.basic
        devices = list(basic.get_devices(create_device))
        assert len(devices) == 1
        # pickle datetime bug
        assert isinstance(devices[0].last_seen, datetime.datetime)
        devices[0].last_seen = datetime.datetime(2019, 3, 13, 16, 40, 53, 180_058)
        if devices[0].boot_time:
            devices[0].boot_time = datetime.datetime(2019, 2, 12, 20, 24, 18, 14110)
        dict_ = devices[0].to_dict()
        del dict_['raw']
        assert dict_ == {
            'id': 'basic_info_cisco-switch.axonius.lan_FOC1115Z2Y5',
            'network_interfaces': [
                {
                    'admin_status': 'Up',
                    'ips': [
                        '192.168.10.6'
                    ],
                    'ips_raw': [
                        3232238086
                    ],
                    'mac': '00:1B:8F:DF:DF:40',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'Vlan1',
                    'operational_status': 'Up',
                    'speed': '1000000000',
                    'subnets': [
                        '192.168.10.0/24'
                    ],
                    'vlan_list': []
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:01',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/1',
                    'operational_status': 'Up',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:02',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/2',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:03',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/3',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:04',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/4',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:05',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/5',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:06',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/6',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:07',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/7',
                    'operational_status': 'Up',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:08',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/8',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:09',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/9',
                    'operational_status': 'Up',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:0A',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/10',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:0B',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/11',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:0C',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/12',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:0D',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/13',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:0E',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/14',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:0F',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/15',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:10',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/16',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:11',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/17',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:12',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/18',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:13',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/19',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:14',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/20',
                    'operational_status': 'Up',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:15',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/21',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:16',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/22',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:17',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/23',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:18',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/24',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:19',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/25',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:1A',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/26',
                    'operational_status': 'Up',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:1B',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/27',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:1C',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/28',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:1D',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/29',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:1E',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/30',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:1F',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/31',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:20',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/32',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:21',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/33',
                    'operational_status': 'Up',
                    'speed': '100000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:22',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/34',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:23',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/35',
                    'operational_status': 'Up',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:24',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/36',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:25',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/37',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:26',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/38',
                    'operational_status': 'Up',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:27',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/39',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Down',
                    'mac': '00:1B:8F:DF:DF:28',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/40',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:29',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/41',
                    'operational_status': 'Up',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'VLAN0099',
                            'tagid': 99
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:2A',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/42',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:2B',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/43',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:2C',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/44',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:2D',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/45',
                    'operational_status': 'Down',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:2E',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/46',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:2F',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/47',
                    'operational_status': 'Down',
                    'speed': '10000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mac': '00:1B:8F:DF:DF:30',
                    'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                    'mtu': '1500',
                    'name': 'GigabitEthernet0/48',
                    'operational_status': 'Up',
                    'speed': '1000000000',
                    'vlan_list': [
                        {
                            'name': 'default',
                            'tagid': 1
                        }
                    ]
                },
                {
                    'admin_status': 'Up',
                    'mtu': '1500',
                    'name': 'Null0',
                    'operational_status': 'Up',
                    'speed': '4294967295',
                    'vlan_list': []
                }
            ],
            'os': {
                'build': 'Cisco IOS Software, C2960 Software (C2960-LANBASEK9-M), Version 12.2(55)SE10, RELEASE SOFTWARE (fc2)\r\nTechnical Support: http://www.cisco.com/techsupport\r\nCopyright (c) 1986-2015 by Cisco Systems, Inc.\r\nCompiled Wed 11-Feb-15 11:46 by prod_rel_team',
                'type': 'Cisco'
            },
            'port_access': [
                {
                    'auth_fail_max_attempts': 3,
                    'auth_fail_vlan_number': 0,
                    'guest_vlan_number': 0,
                    'name': 'GigabitEthernet0/40',
                    'operation_vlan_number': 0,
                    'operation_vlan_type': 'operational',
                    'port_mode': 'singleHost'
                },
                {
                    'auth_fail_max_attempts': 3,
                    'auth_fail_vlan_number': 0,
                    'guest_vlan_number': 0,
                    'name': 'GigabitEthernet0/41',
                    'operation_vlan_number': 0,
                    'operation_vlan_type': 'operational',
                    'port_mode': 'singleHost'
                }
            ],
            PORT_SECURITY_FIELD: [
                {
                    'name': 'GigabitEthernet0/40',
                    'status': 'securedown',
                    'sticky': False,
                    'max_addr': 5,
                    'violation_action': 'dropNotify',
                    'violation_count': 0,
                    'entries': [
                        {'mac_address': '34:75:C7:E9:62:11', 'type': 'Dynamic', 'remaining_age_time': 0, 'vlan_id': '1'},
                        {'mac_address': '34:75:C7:E9:67:22', 'type': 'Dynamic', 'remaining_age_time': 0, 'vlan_id': '1'}
                    ],
                },
                {
                    'name': 'GigabitEthernet0/41',
                    'status': 'secureup',
                    'sticky': True,
                    'max_addr': 10,
                    'violation_action': 'shutdown',
                    'violation_count': 0,
                    'entries': [
                        {'mac_address': '00:0C:6C:0A:4A:AA', 'type': 'Sticky', 'remaining_age_time': 0, 'vlan_id': '12'},
                        {'mac_address': '00:0C:6C:0A:4E:EB', 'type': 'Sticky', 'remaining_age_time': 0, 'vlan_id': '12'},
                        {'mac_address': '00:50:B6:87:92:98', 'type': 'Sticky', 'remaining_age_time': 0, 'vlan_id': '12'},
                        {'mac_address': '34:75:A7:E9:A8:C9', 'type': 'Sticky', 'remaining_age_time': 0, 'vlan_id': '99'},
                        {'mac_address': '34:75:C7:E9:88:88', 'type': 'Sticky', 'remaining_age_time': 0, 'vlan_id': '99'},
                        {'mac_address': '34:75:C7:E9:A8:C9', 'type': 'Dynamic', 'remaining_age_time': 0, 'vlan_id': '99'},
                    ],
                }
            ],
            'hostname': 'cisco-switch.axonius.lan',
            'boot_time': datetime.datetime(2019, 2, 12, 20, 24, 18, 14110),
            'device_model': 'WS-C2960G-48TC-L',
            'adapter_properties': ['Network', 'Manager'],
            'device_serial': 'FOC1115Z2Y5',
            'uptime': 34,
            'fetch_proto': 'CLIENT',
            'last_seen': datetime.datetime(2019, 3, 13, 16, 40, 53, 180_058),
        }


def test_basic_info_devices(mocks):
    basic = mocks.basic
    devices = list(basic.get_devices(create_device))
    assert len(devices) == 1
    # pickle datetime bug
    assert isinstance(devices[0].last_seen, datetime.datetime)
    devices[0].last_seen = datetime.datetime(2019, 3, 13, 16, 40, 53, 180_058)
    if devices[0].boot_time:
        devices[0].boot_time = datetime.datetime(2019, 2, 12, 20, 24, 18, 14110)
    dict_ = devices[0].to_dict()
    del dict_['raw']
    assert dict_ == {
        'id': 'basic_info_cisco-switch.axonius.lan_FOC1115Z2Y5',
        'network_interfaces': [
            {
                'admin_status': 'Up',
                'ips': [
                    '192.168.10.6'
                ],
                'ips_raw': [
                    3232238086
                ],
                'mac': '00:1B:8F:DF:DF:40',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'Vlan1',
                'operational_status': 'Up',
                'speed': '1000000000',
                'subnets': [
                    '192.168.10.0/24'
                ],
                'vlan_list': []
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:01',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/1',
                'operational_status': 'Up',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:02',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/2',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:03',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/3',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:04',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/4',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:05',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/5',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:06',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/6',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:07',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/7',
                'operational_status': 'Up',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:08',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/8',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:09',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/9',
                'operational_status': 'Up',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:0A',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/10',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:0B',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/11',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:0C',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/12',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:0D',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/13',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:0E',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/14',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:0F',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/15',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:10',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/16',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:11',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/17',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:12',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/18',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:13',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/19',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:14',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/20',
                'operational_status': 'Up',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:15',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/21',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:16',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/22',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:17',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/23',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:18',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/24',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:19',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/25',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:1A',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/26',
                'operational_status': 'Up',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:1B',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/27',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:1C',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/28',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:1D',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/29',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:1E',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/30',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:1F',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/31',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:20',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/32',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:21',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/33',
                'operational_status': 'Up',
                'speed': '100000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:22',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/34',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:23',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/35',
                'operational_status': 'Up',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:24',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/36',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:25',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/37',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:26',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/38',
                'operational_status': 'Up',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:27',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/39',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Down',
                'mac': '00:1B:8F:DF:DF:28',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/40',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:29',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/41',
                'operational_status': 'Up',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'VLAN0099',
                        'tagid': 99
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:2A',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/42',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:2B',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/43',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:2C',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/44',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:2D',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/45',
                'operational_status': 'Down',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:2E',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/46',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:2F',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/47',
                'operational_status': 'Down',
                'speed': '10000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mac': '00:1B:8F:DF:DF:30',
                'manufacturer': 'Cisco Systems, Inc (80 West Tasman Drive San Jose CA US 94568 )',
                'mtu': '1500',
                'name': 'GigabitEthernet0/48',
                'operational_status': 'Up',
                'speed': '1000000000',
                'vlan_list': [
                    {
                        'name': 'default',
                        'tagid': 1
                    }
                ]
            },
            {
                'admin_status': 'Up',
                'mtu': '1500',
                'name': 'Null0',
                'operational_status': 'Up',
                'speed': '4294967295',
                'vlan_list': []
            }
        ],
        'os': {
            'build': 'Cisco IOS Software, C2960 Software (C2960-LANBASEK9-M), Version 12.2(55)SE10, RELEASE SOFTWARE (fc2)\r\nTechnical Support: http://www.cisco.com/techsupport\r\nCopyright (c) 1986-2015 by Cisco Systems, Inc.\r\nCompiled Wed 11-Feb-15 11:46 by prod_rel_team',
            'type': 'Cisco'
        },
        'port_access': [
            {
                'auth_fail_max_attempts': 3,
                'auth_fail_vlan_number': 0,
                'guest_vlan_number': 0,
                'name': 'GigabitEthernet0/40',
                'operation_vlan_number': 0,
                'operation_vlan_type': 'operational',
                'port_mode': 'singleHost'
            },
            {
                'auth_fail_max_attempts': 3,
                'auth_fail_vlan_number': 0,
                'guest_vlan_number': 0,
                'name': 'GigabitEthernet0/41',
                'operation_vlan_number': 0,
                'operation_vlan_type': 'operational',
                'port_mode': 'singleHost'
            }
        ],
        PORT_SECURITY_FIELD: [
            {
                'name': 'GigabitEthernet0/40',
                'status': 'securedown',
                'sticky': False,
                'max_addr': 5,
                'violation_action': 'dropNotify',
                'violation_count': 0,
                'entries': [
                    {'mac_address': '34:75:C7:E9:62:11', 'type': 'Dynamic', 'remaining_age_time': 0, 'vlan_id': '1'},
                    {'mac_address': '34:75:C7:E9:67:22', 'type': 'Dynamic', 'remaining_age_time': 0, 'vlan_id': '1'}
                ],
            },
            {
                'name': 'GigabitEthernet0/41',
                'status': 'secureup',
                'sticky': True,
                'max_addr': 10,
                'violation_action': 'shutdown',
                'violation_count': 0,
                'entries': [
                    {'mac_address': '00:0C:6C:0A:4A:AA', 'type': 'Sticky', 'remaining_age_time': 0, 'vlan_id': '12'},
                    {'mac_address': '00:0C:6C:0A:4E:EB', 'type': 'Sticky', 'remaining_age_time': 0, 'vlan_id': '12'},
                    {'mac_address': '00:50:B6:87:92:98', 'type': 'Sticky', 'remaining_age_time': 0, 'vlan_id': '12'},
                    {'mac_address': '34:75:A7:E9:A8:C9', 'type': 'Sticky', 'remaining_age_time': 0, 'vlan_id': '99'},
                    {'mac_address': '34:75:C7:E9:88:88', 'type': 'Sticky', 'remaining_age_time': 0, 'vlan_id': '99'},
                    {'mac_address': '34:75:C7:E9:A8:C9', 'type': 'Dynamic', 'remaining_age_time': 0, 'vlan_id': '99'},
                ],
            }
        ],
        'hostname': 'cisco-switch.axonius.lan',
        'boot_time': datetime.datetime(2019, 2, 12, 20, 24, 18, 14110),
        'device_model': 'WS-C2960G-48TC-L',
        'adapter_properties': ['Network', 'Manager'],
        'device_serial': 'FOC1115Z2Y5',
        'uptime': 34,
        'fetch_proto': 'CLIENT',
        'last_seen': datetime.datetime(2019, 3, 13, 16, 40, 53, 180_058),
    }
