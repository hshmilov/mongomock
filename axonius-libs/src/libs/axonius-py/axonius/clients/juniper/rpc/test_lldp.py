import logging

from axonius.clients.juniper.device import JuniperDeviceAdapter, create_device
from axonius.clients.juniper.rpc import (parse_lldp, prepare, parse_device)
from axonius.clients.juniper.rpc.mock import LLDP_MOCK, LLDP_MOCK2

logging.basicConfig()


def test_parse_lldp():
    data = prepare(LLDP_MOCK)
    result = parse_lldp([('foo', data)])
    assert len(result) == 1
    assert len(list(result.values())[0]) == 3


def test_create_devcie():
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
    assert raw_result['connected_devices'] == [{'local_iface': 'Ethernet3/29/1',
                                                'remote_iface': 'xe-0/1/1',
                                                'remote_name': 'leaf.sjc04'},
                                               {'local_iface': 'Ethernet3/29/2',
                                                'remote_iface': 'xe-0/3/3',
                                                'remote_name': 'leaf.sjc04'},
                                               {'local_iface': 'Ethernet3/29/3',
                                                'remote_iface': 'xe-2/0/5',
                                                'remote_name': 'leaf.sjc04'},
                                               {'local_iface': 'Ethernet3/42/1',
                                                'remote_iface': 'xe-0/1/1',
                                                'remote_name': 'room1.sjc11'}]
