# pylint: disable=protected-access
import pytest

# pylint: disable=wildcard-import,too-many-lines,line-too-long
from axonius.clients.cisco.abstract import CiscoDevice, InstanceParser
from axonius.clients.cisco.console import *
from axonius.clients.cisco.constants import *

MOCKS = Commands(
    arp='\n'.join(
        [
            'internet  10.0.0.2                -   c000.07a8.0001  arpa   fastethernet0/1',
            'internet  10.0.0.1              206   1133.3377.dead  arpa   fastethernet0/1',
            'internet  192.168.20.30           -   c000.07a8.0000  arpa   fastethernet0/0',
            'internet  192.168.20.18           0   0050.5691.a66b  arpa   fastethernet0/0',
            'internet  192.168.20.1            0   906c.acfe.5bcb  arpa   fastethernet0/0',
            'internet  10.0.0.201              -   c000.07a8.0001  arpa   fastethernet0/1',
        ]
    ),
    dhcp='Bindings from all pools not associated with VRF:\nIP address          Client-ID/\t \t    Lease expiration        Type\n\t\t    Hardware address/\n\t\t    User name\n10.0.0.1            0063.6973.636f.2d31.    Mar 09 2002 12:00 AM    Automatic\n                    3133.332e.3333.3737.\n                    2e64.6561.642d.4661.\n                    302f.30',
    cdp='-------------------------\nDevice ID: dhcp-slave\nEntry address(es): \n  IP address: 10.0.0.1\nPlatform: Cisco 2691,  Capabilities: Switch IGMP \nInterface: FastEthernet0/1,  Port ID (outgoing port): FastEthernet0/0\nHoldtime : 138 sec\n\nVersion :\nCisco IOS Software, 2600 Software (C2691-ENTSERVICESK9-M), Version 12.4(13b), RELEASE SOFTWARE (fc3)\nTechnical Support: http://www.cisco.com/techsupport\nCopyright (c) 1986-2007 by Cisco Systems, Inc.\nCompiled Tue 24-Apr-07 15:33 by prod_rel_team\n\nadvertisement version: 2\nVTP Management Domain: '
    '\nDuplex: half\n',
)


class MockConnectHandler:
    def disconnect(self):
        pass

    @staticmethod
    def send_command_timing(command):
        if command not in COMMANDS:
            raise RuntimeError(f'{command} not implemented')

        return MOCKS[COMMANDS.index(command)]


# pylint: disable=abstract-method


class MockConsoleClient(CiscoConsoleClient):
    def __enter__(self):
        AbstractCiscoClient.__enter__(self)
        self._sess = MockConnectHandler()
        return self


def create_device():
    return CiscoDevice(set(), set())


def print_mocks(ip):
    with CiscoTelnetClient(host=ip, port=23, username='cisco', password='cisco') as c:
        print(f'arp = {repr(c.query_arp_table()._raw_data)}')
        print(f'dhcp = {repr(c.query_dhcp_leases()._raw_data)}')
        print(f'cdp = {repr(c.query_cdp_table()._raw_data)}')


# pylint: disable=redefined-outer-name
@pytest.fixture(scope='session')
def client():
    return MockConsoleClient(host='mock', port='1337', username='cisco', password='cisco')


def test_arp(client):
    with client:
        result = client.query_arp_table()

    expected_parsed_data = [
        {
            'mac': 'C0:00:07:A8:00:01',
            'ip': '10.0.0.2',
            'remote_iface': 'fastethernet0/1',
            'connected_devices': [{'name': 'mock', 'iface': 'fastethernet0/1', 'type': 'Indirect'}],
        },
        {
            'mac': '11:33:33:77:DE:AD',
            'ip': '10.0.0.1',
            'remote_iface': 'fastethernet0/1',
            'connected_devices': [{'name': 'mock', 'iface': 'fastethernet0/1', 'type': 'Indirect'}],
        },
        {
            'mac': 'C0:00:07:A8:00:00',
            'ip': '192.168.20.30',
            'remote_iface': 'fastethernet0/0',
            'connected_devices': [{'name': 'mock', 'iface': 'fastethernet0/0', 'type': 'Indirect'}],
        },
        {
            'mac': '00:50:56:91:A6:6B',
            'ip': '192.168.20.18',
            'remote_iface': 'fastethernet0/0',
            'connected_devices': [{'name': 'mock', 'iface': 'fastethernet0/0', 'type': 'Indirect'}],
        },
        {
            'mac': '90:6C:AC:FE:5B:CB',
            'ip': '192.168.20.1',
            'remote_iface': 'fastethernet0/0',
            'connected_devices': [{'name': 'mock', 'iface': 'fastethernet0/0', 'type': 'Indirect'}],
        },
        {
            'mac': 'C0:00:07:A8:00:01',
            'ip': '10.0.0.201',
            'remote_iface': 'fastethernet0/1',
            'connected_devices': [{'name': 'mock', 'iface': 'fastethernet0/1', 'type': 'Indirect'}],
        },
    ]
    expected_devices = [
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/1'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_C0:00:07:A8:00:01',
            'network_interfaces': [{'ips': ['10.0.0.2'], 'ips_raw': [167_772_162], 'mac': 'C0:00:07:A8:00:01'}],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'fastethernet0/1', 'name': 'mock', 'type': 'Indirect'}],
                'ip': '10.0.0.2',
                'mac': 'C0:00:07:A8:00:01',
                'remote_iface': 'fastethernet0/1',
            },
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/1'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_11:33:33:77:DE:AD',
            'network_interfaces': [{'ips': ['10.0.0.1'], 'ips_raw': [167_772_161], 'mac': '11:33:33:77:DE:AD'}],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'fastethernet0/1', 'name': 'mock', 'type': 'Indirect'}],
                'ip': '10.0.0.1',
                'mac': '11:33:33:77:DE:AD',
                'remote_iface': 'fastethernet0/1',
            },
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/0'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_C0:00:07:A8:00:00',
            'network_interfaces': [{'ips': ['192.168.20.30'], 'ips_raw': [3_232_240_670], 'mac': 'C0:00:07:A8:00:00'}],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'fastethernet0/0', 'name': 'mock', 'type': 'Indirect'}],
                'ip': '192.168.20.30',
                'mac': 'C0:00:07:A8:00:00',
                'remote_iface': 'fastethernet0/0',
            },
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/0'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_00:50:56:91:A6:6B',
            'network_interfaces': [
                {
                    'ips': ['192.168.20.18'],
                    'ips_raw': [3_232_240_658],
                    'mac': '00:50:56:91:A6:6B',
                    'manufacturer': 'VMware, Inc. (3401 Hillview Avenue ' 'PALO ALTO CA US 94304 )',
                }
            ],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'fastethernet0/0', 'name': 'mock', 'type': 'Indirect'}],
                'ip': '192.168.20.18',
                'mac': '00:50:56:91:A6:6B',
                'remote_iface': 'fastethernet0/0',
            },
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/0'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_90:6C:AC:FE:5B:CB',
            'network_interfaces': [
                {
                    'ips': ['192.168.20.1'],
                    'ips_raw': [3_232_240_641],
                    'mac': '90:6C:AC:FE:5B:CB',
                    'manufacturer': 'Fortinet, Inc. (899 Kifer Road ' 'Sunnyvale California US 94086 )',
                }
            ],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'fastethernet0/0', 'name': 'mock', 'type': 'Indirect'}],
                'ip': '192.168.20.1',
                'mac': '90:6C:AC:FE:5B:CB',
                'remote_iface': 'fastethernet0/0',
            },
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/1'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_C0:00:07:A8:00:01',
            'network_interfaces': [{'ips': ['10.0.0.201'], 'ips_raw': [167_772_361], 'mac': 'C0:00:07:A8:00:01'}],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'fastethernet0/1', 'name': 'mock', 'type': 'Indirect'}],
                'ip': '10.0.0.201',
                'mac': 'C0:00:07:A8:00:01',
                'remote_iface': 'fastethernet0/1',
            },
        },
    ]
    assert result.get_parsed_data() == expected_parsed_data

    devices = list(map(lambda device: device.to_dict(), result.get_devices(create_device)))
    assert len(devices) == 6
    assert devices == expected_devices


def test_cdp(client):
    expected_devices = [
        {
            'id': 'cdp_dhcp-slave',
            'network_interfaces': [{'ips': ['10.0.0.1'], 'ips_raw': [167_772_161], 'name': 'FastEthernet0/0'}],
            'connected_devices': [
                {'remote_name': 'mock', 'connection_type': 'Direct', 'remote_ifaces': [{'name': 'FastEthernet0/1'}]}
            ],
            'hostname': 'dhcp-slave',
            'device_model': 'Cisco 2691',
            'os': {
                'type': 'Cisco',
                'build': 'Cisco IOS Software, 2600 Software (C2691-ENTSERVICESK9-M), Version 12.4(13b), RELEASE SOFTWARE (fc3)\nTechnical Support: http://www.cisco.com/techsupport\nCopyright (c) 1986-2007 by Cisco Systems, Inc.\nCompiled Tue 24-Apr-07 15:33 by prod_rel_team',
            },
            'raw': {
                'ip': '10.0.0.1',
                'version': 'Cisco IOS Software, 2600 Software (C2691-ENTSERVICESK9-M), Version 12.4(13b), RELEASE SOFTWARE (fc3)\nTechnical Support: http://www.cisco.com/techsupport\nCopyright (c) 1986-2007 by Cisco Systems, Inc.\nCompiled Tue 24-Apr-07 15:33 by prod_rel_team',
                'hostname': 'dhcp-slave',
                'remote_iface': 'FastEthernet0/1',
                'iface': 'FastEthernet0/0',
                'device_model': 'Cisco 2691',
                'connected_devices': [{'name': 'mock', 'iface': 'FastEthernet0/1', 'type': 'Direct'}],
            },
            'fetch_proto': 'CDP',
            'adapter_properties': ['Network'],
        }
    ]

    expected_parsed_data = [
        {
            'connected_devices': [{'iface': 'FastEthernet0/1', 'name': 'mock', 'type': 'Direct'}],
            'device_model': 'Cisco 2691',
            'hostname': 'dhcp-slave',
            'iface': 'FastEthernet0/0',
            'ip': '10.0.0.1',
            'remote_iface': 'FastEthernet0/1',
            'version': 'Cisco IOS Software, 2600 Software (C2691-ENTSERVICESK9-M), '
                       'Version 12.4(13b), RELEASE SOFTWARE (fc3)\n'
                       'Technical Support: http://www.cisco.com/techsupport\n'
                       'Copyright (c) 1986-2007 by Cisco Systems, Inc.\n'
                       'Compiled Tue 24-Apr-07 15:33 by prod_rel_team',
        }
    ]

    with client:
        result = client.query_cdp_table()
    assert result.get_parsed_data() == expected_parsed_data
    devices = list(map(lambda device: device.to_dict(), result.get_devices(create_device)))
    assert len(devices) == 1
    assert devices == expected_devices


def test_dhcp(client):
    expected_parsed_data = [
        {
            'connected_devices': [{'iface': 'Fa0/0', 'name': 'mock', 'type': 'Indirect'}],
            'ip': '10.0.0.1',
            'ip-expires': 'Mar 09 2002 12:00 AM',
            'ip-type': 'Automatic',
            'mac': '11:33:33:77:DE:AD',
            'remote_iface': 'Fa0/0',
        }
    ]

    expected_devices = [
        {
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'Fa0/0'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'DHCP',
            'id': 'dhcp_11:33:33:77:DE:AD',
            'network_interfaces': [{'ips': ['10.0.0.1'], 'ips_raw': [167_772_161], 'mac': '11:33:33:77:DE:AD'}],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'Fa0/0', 'name': 'mock', 'type': 'Indirect'}],
                'ip': '10.0.0.1',
                'ip-expires': 'Mar 09 2002 12:00 AM',
                'ip-type': 'Automatic',
                'mac': '11:33:33:77:DE:AD',
                'remote_iface': 'Fa0/0',
            },
        }
    ]

    with client:
        result = client.query_dhcp_leases()
    assert result.get_parsed_data() == expected_parsed_data
    devices = list(map(lambda device: device.to_dict(), result.get_devices(create_device)))
    assert len(devices) == 1
    assert devices == expected_devices


def test_instance_parser(client):
    expected = [
        {
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'Fa0/0'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'DHCP',
            'id': 'dhcp_11:33:33:77:DE:AD',
            'network_interfaces': [{'ips': ['10.0.0.1'], 'ips_raw': [167_772_161], 'mac': '11:33:33:77:DE:AD'}],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'Fa0/0', 'name': 'mock', 'type': 'Indirect'}],
                'ip': '10.0.0.1',
                'ip-expires': 'Mar 09 2002 12:00 AM',
                'ip-type': 'Automatic',
                'mac': '11:33:33:77:DE:AD',
                'remote_iface': 'Fa0/0',
            },
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Direct', 'remote_ifaces': [{'name': 'FastEthernet0/1'}], 'remote_name': 'mock'}
            ],
            'device_model': 'Cisco 2691',
            'fetch_proto': 'CDP',
            'hostname': 'dhcp-slave',
            'id': 'cdp_dhcp-slave',
            'network_interfaces': [{'mac': '11:33:33:77:DE:AD', 'name': 'FastEthernet0/0'}],
            'os': {
                'build': 'Cisco IOS Software, 2600 Software (C2691-ENTSERVICESK9-M), '
                         'Version 12.4(13b), RELEASE SOFTWARE (fc3)\n'
                         'Technical Support: http://www.cisco.com/techsupport\n'
                         'Copyright (c) 1986-2007 by Cisco Systems, Inc.\n'
                         'Compiled Tue 24-Apr-07 15:33 by prod_rel_team',
                'type': 'Cisco',
            },
            'raw': {
                'connected_devices': [{'iface': 'FastEthernet0/1', 'name': 'mock', 'type': 'Direct'}],
                'device_model': 'Cisco 2691',
                'hostname': 'dhcp-slave',
                'interface': {
                    '0': {
                        'description': 'FastEthernet0/0',
                        'ips': [{'address': '10.0.0.1'}],
                        'mac': '11:33:33:77:DE:AD',
                    }
                },
                'version': 'Cisco IOS Software, 2600 Software '
                           '(C2691-ENTSERVICESK9-M), Version 12.4(13b), RELEASE '
                           'SOFTWARE (fc3)\n'
                           'Technical Support: http://www.cisco.com/techsupport\n'
                           'Copyright (c) 1986-2007 by Cisco Systems, Inc.\n'
                           'Compiled Tue 24-Apr-07 15:33 by prod_rel_team',
            },
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/1'}], 'remote_name': 'mock'},
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/1'}], 'remote_name': 'mock'},
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_C0:00:07:A8:00:01',
            'network_interfaces': [{'mac': 'C0:00:07:A8:00:01'}],
            'os': {},
            'raw': {
                'connected_devices': [
                    {'iface': 'fastethernet0/1', 'name': 'mock', 'type': 'Indirect'},
                    {'iface': 'fastethernet0/1', 'name': 'mock', 'type': 'Indirect'},
                ],
                'mac': 'C0:00:07:A8:00:01',
                'related_ips': ['10.0.0.2', '10.0.0.201'],
            },
            'related_ips': {'ips': ['10.0.0.2', '10.0.0.201'], 'ips_raw': [167_772_162, 167_772_361]},
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/1'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_11:33:33:77:DE:AD',
            'network_interfaces': [{'mac': '11:33:33:77:DE:AD'}],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'fastethernet0/1', 'name': 'mock', 'type': 'Indirect'}],
                'mac': '11:33:33:77:DE:AD',
                'related_ips': ['10.0.0.1'],
            },
            'related_ips': {'ips': ['10.0.0.1'], 'ips_raw': [167_772_161]},
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/0'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_C0:00:07:A8:00:00',
            'network_interfaces': [{'mac': 'C0:00:07:A8:00:00'}],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'fastethernet0/0', 'name': 'mock', 'type': 'Indirect'}],
                'mac': 'C0:00:07:A8:00:00',
                'related_ips': ['192.168.20.30'],
            },
            'related_ips': {'ips': ['192.168.20.30'], 'ips_raw': [3_232_240_670]},
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/0'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_00:50:56:91:A6:6B',
            'network_interfaces': [
                {
                    'mac': '00:50:56:91:A6:6B',
                    'manufacturer': 'VMware, Inc. (3401 Hillview Avenue ' 'PALO ALTO CA US 94304 )',
                }
            ],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'fastethernet0/0', 'name': 'mock', 'type': 'Indirect'}],
                'mac': '00:50:56:91:A6:6B',
                'related_ips': ['192.168.20.18'],
            },
            'related_ips': {'ips': ['192.168.20.18'], 'ips_raw': [3_232_240_658]},
        },
        {
            'adapter_properties': ['Network'],
            'connected_devices': [
                {'connection_type': 'Indirect', 'remote_ifaces': [{'name': 'fastethernet0/0'}], 'remote_name': 'mock'}
            ],
            'fetch_proto': 'ARP',
            'id': 'arp_90:6C:AC:FE:5B:CB',
            'network_interfaces': [
                {
                    'mac': '90:6C:AC:FE:5B:CB',
                    'manufacturer': 'Fortinet, Inc. (899 Kifer Road ' 'Sunnyvale California US 94086 )',
                }
            ],
            'os': {},
            'raw': {
                'connected_devices': [{'iface': 'fastethernet0/0', 'name': 'mock', 'type': 'Indirect'}],
                'mac': '90:6C:AC:FE:5B:CB',
                'related_ips': ['192.168.20.1'],
            },
            'related_ips': {'ips': ['192.168.20.1'], 'ips_raw': [3_232_240_641]},
        },
    ]

    with client:
        results = client.query_all()
        devices = list(InstanceParser(results).get_devices(create_device))
    devices = list(map(lambda device: device.to_dict(), devices))
    assert devices == expected
