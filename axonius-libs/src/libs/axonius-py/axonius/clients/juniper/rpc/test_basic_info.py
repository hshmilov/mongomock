import logging
import pytest

from axonius.clients.juniper.device import JuniperDeviceAdapter, create_device
from axonius.clients.juniper.rpc import (parse_device, parse_hardware,
                                         parse_interface_list, parse_version,
                                         parse_vlans, prepare)
from axonius.clients.juniper.rpc.mock import (HARDWARE_MOCK, INTERFACE_MOCK,
                                              VERSION_MOCK, VLAN_MOCK,
                                              VLAN_MOCK2, VERSION_MOCK2,
                                              mock_query_basic_info)

logging.basicConfig()


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


@pytest.mark.skip(reason='not supported yet')
def test_parse_vlans2():
    data = prepare(VLAN_MOCK2)
    result = parse_vlans(data)
    assert len(result) == 4


def test_basic_info():
    result = parse_device('Juniper Device', mock_query_basic_info())
    assert result


def test_create_device():
    result = parse_device('Juniper Device', mock_query_basic_info())
    result = list(create_device(lambda: JuniperDeviceAdapter(set(), set()), 'Juniper Device', result))
    assert result
