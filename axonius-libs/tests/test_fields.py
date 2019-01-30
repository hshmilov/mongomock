from enum import Enum, auto

import pytest

from axonius.devices.device_adapter import (AdapterProperty, DeviceAdapter,
                                            Field, ListField)


class ExampleEnum(Enum):
    One = auto()
    Two = auto()


class MyDeviceAdapter(DeviceAdapter):
    props = ListField(str, 'test properties', enum=AdapterProperty)


class MyDeviceAdapter2(DeviceAdapter):
    props = ListField(str, 'test properties', enum=['Asdf', 'Qwetr', AdapterProperty.Agent])
    props2 = Field(str, 'test properties2', enum=['Asdf', 'Qwetr'])
    props3 = Field(str, 'test properties3', enum=AdapterProperty)


class MyDeviceAdapter3(DeviceAdapter):
    test = ListField(str, 'test')
    test2 = Field(str, 'test2')
    test3 = Field(int, 'test3')


class MyDeviceAdapter4(DeviceAdapter):
    test = Field(int, 'inttest', enum=[1, 2, 3])
    test2 = Field(int, 'inttest2', enum=ExampleEnum)


def test_listfield_enum():
    device = MyDeviceAdapter(set(), set())
    device.props = [AdapterProperty.Agent, 'network']
    a = device.to_dict()
    assert a['props'] == ['Agent', 'Network']

    device = MyDeviceAdapter2(set(), set())
    device.props = [AdapterProperty.Agent, 'agent', 'Asdf']
    device.props2 = 'Asdf'
    device.props3 = 'Agent'
    a = device.to_dict()
    assert a['props'] == ['Agent', 'Agent', 'Asdf']
    assert a['props2'] == 'Asdf'
    assert a['props3'] == 'Agent'


def test_int_enum():
    device = MyDeviceAdapter4(set(), set())
    device.test = 1
    device.test2 = ExampleEnum.Two
    assert device.to_dict()['test2'] == 'Two'
    assert device.to_dict()['test'] == 1
    device.test2 = ExampleEnum.Two.value
    assert device.to_dict()['test2'] == 'Two'
    assert device.to_dict()['test'] == 1
    device.test2 = 2
    assert device.to_dict()['test2'] == 'Two'
    assert device.to_dict()['test'] == 1


def test_none_list():
    device = MyDeviceAdapter3(set(), set())
    device.test2 = None

    with pytest.raises(KeyError) as e:
        value = device.test2

    device.test2 = ''

    with pytest.raises(KeyError) as e:
        value = device.test2

    device.test2 = 0

    with pytest.raises(KeyError) as e:
        value = device.test2

    with pytest.raises(TypeError) as e:
        device.test = [None]

    with pytest.raises(TypeError) as e:
        device.test.append(None)

    with pytest.raises(TypeError) as e:
        device.test = ['asdf', None]

    device.test = ['asdf', '']
    device.test = None

    device.test3 = 0
    value = device.test3


def test_exists_with_empty_first():
    device = MyDeviceAdapter4(set(), set())
    device.network_interfaces = []
    device.add_nic(ips=['1.1.1.1'])
    assert 'network_interfaces' in device.all_fields_found


def test_exists():
    device = MyDeviceAdapter4(set(), set())
    device.add_nic(ips=['1.1.1.1'])
    assert 'network_interfaces' in device.all_fields_found
