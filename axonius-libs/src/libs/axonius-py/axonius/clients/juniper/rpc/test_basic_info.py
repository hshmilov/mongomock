import logging
import pytest

from axonius.clients.juniper.device import JuniperDeviceAdapter, create_device, update_connected
from axonius.clients.juniper.rpc import (parse_device, parse_hardware,
                                         parse_interface_list, parse_version,
                                         parse_vlans, prepare, parse_lldp, parse_base_mac)

from axonius.clients.juniper.rpc.mock import (HARDWARE_MOCK, INTERFACE_MOCK,
                                              VERSION_MOCK, VLAN_MOCK,
                                              VLAN_MOCK2, VERSION_MOCK2, BASE_MAC_MOCK,
                                              mock_query_basic_info, LLDP_MOCK, LLDP_MOCK2)

logging.basicConfig()


def test_parse_lldp():
    data = prepare(LLDP_MOCK)
    result = parse_lldp([('foo', data)])
    assert len(result) == 1
    assert len(list(result.values())[0]) == 3


def test_create_lldp_device():
    data = [('leaf.sjc04', prepare(LLDP_MOCK)),
            ('room1.sjc11', prepare(LLDP_MOCK2))]

    result = parse_device('LLDP Device', data)
    result = list(create_device(lambda: JuniperDeviceAdapter(
        set(), set()), 'LLDP Device', result))
    assert len(result) == 2

    raw_result = result[0].to_dict()
    assert all(map(lambda x: x in raw_result, [
        'name', 'network_interfaces', 'connected_devices']))
    assert len(raw_result['connected_devices']) == 4
    assert raw_result['connected_devices'] == [{'connection_type': 'Direct',
                                                'local_ifaces': [{'name': 'Ethernet3/29/1'}],
                                                'remote_ifaces': [{'name': 'xe-0/1/1'}],
                                                'remote_name': 'leaf.sjc04'},
                                               {'connection_type': 'Direct',
                                                'local_ifaces': [{'name': 'Ethernet3/29/2'}],
                                                'remote_ifaces': [{'name':  'xe-0/3/3'}],
                                                'remote_name': 'leaf.sjc04'},
                                               {'connection_type': 'Direct',
                                                'local_ifaces': [{'name': 'Ethernet3/29/3'}],
                                                'remote_ifaces': [{'name': 'xe-2/0/5'}],
                                                'remote_name': 'leaf.sjc04'},
                                               {'connection_type': 'Direct',
                                                'local_ifaces': [{'name': 'Ethernet3/42/1'}],
                                                'remote_ifaces': [{'name': 'xe-0/1/1'}],
                                                'remote_name': 'room1.sjc11'}]


def test_interface_list():
    data = prepare(INTERFACE_MOCK)
    result = parse_interface_list(data)[0]
    assert len(result) == 7


def test_version():
    data = prepare(VERSION_MOCK)
    result = parse_version(data)
    assert all([x in result for x in ['version', 'host-name', 'product-model']])


@pytest.mark.skip(reason='not supported yet')
def test_version2():
    data = prepare(VERSION_MOCK2)
    result = parse_version(data)
    #assert all([x in result for x in ['version', 'host-name', 'product-model']])


def test_parse_hardware():
    data = prepare(HARDWARE_MOCK)
    result = parse_hardware(data)
    assert all([x in result for x in ['serial-number', 'description']])


def test_parse_vlans():
    data = prepare(VLAN_MOCK)
    result = parse_vlans(data)
    assert len(result) == 4


def test_parse_base_mac():
    data = prepare(BASE_MAC_MOCK)
    result = parse_base_mac(data)
    assert len(result) == 1


def test_parse_vlans2():
    data = prepare(VLAN_MOCK2)
    result = parse_vlans(data)
    assert len(result) == 7

    vlan_mock = VLAN_MOCK2.replace('ae0.0', 'em0.0').replace('ae10.0', 'em1.0')
    mock = mock_query_basic_info()
    mock[1].append(('vlans', vlan_mock))
    result = parse_device('Juniper Device', mock)
    result2 = list(create_device(lambda: JuniperDeviceAdapter(set(), set()), 'Juniper Device', result))[0]
    result2.set_raw({})


def test_basic_info():
    result = parse_device('Juniper Device', mock_query_basic_info())
    assert result


def test_create_juniper_device():
    result = parse_device('Juniper Device', mock_query_basic_info())
    result2 = list(create_device(lambda: JuniperDeviceAdapter(set(), set()), 'Juniper Device', result))
    em0 = list(filter(lambda iface: iface['name'] == 'em0.0', result2[0].network_interfaces))[0].to_dict()
    assert result2
    assert result
    assert len(em0['vlan_list']) == 1
    assert em0['port_type'] == 'Access'

    base_mac0 = list(filter(lambda iface: iface['name'] == 'base-mac0', result2[0].network_interfaces))[0].to_dict()
    assert base_mac0


def test_update_connected():
    result = parse_device('Juniper Device', mock_query_basic_info())
    result2 = list(create_device(lambda: JuniperDeviceAdapter(set(), set()), 'Juniper Device', result))

    lldp_mock = LLDP_MOCK.replace('xe-0/1/1', 'em0.0')
    result = parse_device('LLDP Device', [('juniper-R1', prepare(lldp_mock))])
    result = list(create_device(lambda: JuniperDeviceAdapter(
        set(), set()), 'LLDP Device', result))

    result = update_connected(result + result2)

    raw_result = result[0].to_dict()
    assert raw_result['connected_devices'] == [{'connection_type': 'Direct',
                                                'local_ifaces': [{'name': 'Ethernet3/29/1'}],
                                                'remote_ifaces': [{'name': 'em0.0',
                                                                   'port_type': 'Access'}],
                                                'remote_name': 'juniper-R1'},
                                               {'connection_type': 'Direct',
                                                'local_ifaces': [{'name': 'Ethernet3/29/2'}],
                                                'remote_ifaces': [{'name':  'xe-0/3/3'}],
                                                'remote_name': 'juniper-R1'},
                                               {'connection_type': 'Direct',
                                                'local_ifaces': [{'name': 'Ethernet3/29/3'}],
                                                'remote_ifaces': [{'name': 'xe-2/0/5'}],
                                                'remote_name': 'juniper-R1'}]


def test_version_patch():
    data = mock_query_basic_info()
    del data[1][2]
    result = parse_device('Juniper Device', data)
    result2 = list(create_device(lambda: JuniperDeviceAdapter(set(), set()), 'Juniper Device', result))
    assert result['version']['host-name'] == 'Juniper-R1'
    assert result2[0].hostname == 'Juniper-R1'
