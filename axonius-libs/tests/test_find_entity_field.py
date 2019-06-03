#!/usr/bin/env python3

import time

from axonius.devices.device_adapter import (DeviceAdapter,
                                            DeviceAdapterConnectedHardware,
                                            Field, ListField)
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.gui_helpers import (find_entity_field,
                                       merge_entities_fields,
                                       parse_entity_fields)

# pylint: disable=line-too-long


class MyObject(SmartJsonClass):
    test = Field(str, 'test')
    list_test = ListField(str, 'list_test')
    list_test_int = ListField(int, 'list_test_int')
    int_test = Field(int, 'int_test')
    hostname = Field(str, 'hostname')


class MyDeviceAdapter(DeviceAdapter):
    test = Field(str, 'test')
    list_test = ListField(str, 'list_test')
    list_test_int = ListField(int, 'list_test_int')
    object_test = Field(MyObject, 'object_test')
    object_list_test = ListField(MyObject, 'object_list_test')
    int_test = Field(int, 'int_test')


def test_basic_string_logic():
    device = MyDeviceAdapter(set(), set())
    device.test = 'qwer'

    assert find_entity_field(device.to_dict(), 'test') == 'qwer'

    device2 = MyDeviceAdapter(set(), set())
    device2.test = 'qwer'

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'test') == ['qwer']

    device2.test = 'else'

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'test') == ['qwer', 'else']

    device2.test = 'qwer2'

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'test') == ['qwer', 'qwer2']

    device2.test = ''

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'test') == ['qwer']


def test_hostname_logic():
    device = MyDeviceAdapter(set(), set())
    device.hostname = 'cisco-switch'

    device2 = MyDeviceAdapter(set(), set())
    device2.hostname = 'cisco-switch.axonius.lan'

    device3 = MyDeviceAdapter(set(), set())
    assert parse_entity_fields([device.to_dict(), device2.to_dict(), device3.to_dict()],
                               ['hostname']) == {'hostname': ['cisco-switch']}

    device2.hostname = 'cisco-switc1'

    result = parse_entity_fields([device.to_dict(), device2.to_dict(), device3.to_dict()], ['hostname'])
    assert result == {'hostname': ['cisco-switch', 'cisco-switc1']}


def test_list_logic():
    device = MyDeviceAdapter(set(), set())
    device.list_test = ['asdf', 'qwer', 'asdfqwer']

    assert find_entity_field(device.to_dict(), 'list_test') == ['asdf', 'qwer', 'asdfqwer']

    device2 = MyDeviceAdapter(set(), set())
    device2.list_test = ['asdf', 'qwer', 'asdfqwer']

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test') == ['asdf', 'qwer', 'asdfqwer']

    device2.list_test = ['qwer', 'asdfqwer', 'asdf']

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test') == ['asdf', 'qwer', 'asdfqwer']

    device2.list_test = ['qwer', 'asdf']

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test') == ['asdf', 'qwer', 'asdfqwer']

    device2.list_test = ['else']

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test') == ['asdf', 'qwer', 'asdfqwer', 'else']

    device2.list_test = []

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test') == ['asdf', 'qwer', 'asdfqwer']

    device2.list_test = ['qwer2']

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test') == [
        'asdf', 'qwer', 'asdfqwer', 'qwer2']


def test_list_int_logic():
    device = MyDeviceAdapter(set(), set())
    device.list_test_int = [1, 2, 3]

    assert find_entity_field(device.to_dict(), 'list_test_int') == [1, 2, 3]
    device2 = MyDeviceAdapter(set(), set())
    device2.list_test_int = [1, 2, 3]

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test_int') == [1, 2, 3]

    device2.list_test_int = [2, 3, 1]

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test_int') == [1, 2, 3]

    device2.list_test_int = [2, 3]

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test_int') == [1, 2, 3]

    device2.list_test_int = [4]

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test_int') == [1, 2, 3, 4]

    device2.list_test_int = []

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test_int') == [1, 2, 3]

    device2.list_test_int = [23]

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test_int') == [1, 2, 3, 23]

    device2.list_test_int = [1, 2, 3, 4]
    assert find_entity_field([device.to_dict(), device2.to_dict()], 'list_test_int') == [1, 2, 3, 4]
    assert find_entity_field([device2.to_dict(), device.to_dict()], 'list_test_int') == [1, 2, 3, 4]


def test_object_str_logic():
    device = MyDeviceAdapter(set(), set())
    device.object_test = MyObject()
    device.object_test.test = 'qwer'

    assert find_entity_field(device.to_dict(), 'object_test.test') == 'qwer'

    device2 = MyDeviceAdapter(set(), set())
    device2.object_test = MyObject()
    device2.object_test.test = 'qwer'

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'object_test.test') == ['qwer']

    device2.object_test.test = 'else'

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'object_test.test') == ['qwer', 'else']

    device2.object_test.test = 'qwer2'

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'object_test.test') == ['qwer', 'qwer2']

    device2.object_test.test = ''

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'object_test.test') == ['qwer']


def test_object_list_logic():
    device = MyDeviceAdapter(set(), set())
    device.object_test = MyObject()
    device.object_test.list_test = ['asdf', 'qwer', 'asdfqwer']

    assert find_entity_field(device.to_dict(), 'object_test.list_test') == ['asdf', 'qwer', 'asdfqwer']

    device2 = MyDeviceAdapter(set(), set())
    device2.object_test = MyObject()
    device2.object_test.list_test = ['asdf', 'qwer', 'asdfqwer']

    assert find_entity_field([device.to_dict(), device2.to_dict()],
                             'object_test.list_test') == ['asdf', 'qwer', 'asdfqwer']

    device2.object_test.list_test = ['qwer', 'asdfqwer', 'asdf']

    assert find_entity_field([device.to_dict(), device2.to_dict()],
                             'object_test.list_test') == ['asdf', 'qwer', 'asdfqwer']

    device2.object_test.list_test = ['qwer', 'asdf']

    assert find_entity_field([device.to_dict(), device2.to_dict()],
                             'object_test.list_test') == ['asdf', 'qwer', 'asdfqwer']

    device2.object_test.list_test = ['else']

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'object_test.list_test') == [
        'asdf', 'qwer', 'asdfqwer', 'else']

    device2.object_test.list_test = []

    assert find_entity_field([device.to_dict(), device2.to_dict()],
                             'object_test.list_test') == ['asdf', 'qwer', 'asdfqwer']

    device2.object_test.list_test = ['qwer2']

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'object_test.list_test') == [
        'asdf', 'qwer', 'asdfqwer', 'qwer2']


def test_object_list_and_str_logic():
    device = MyDeviceAdapter(set(), set())
    device.object_test = MyObject()
    device.object_test.list_test = ['asdf', 'qwer', 'asdfqwer']
    device.object_test.test = 'asdf'

    device2 = MyDeviceAdapter(set(), set())
    device2.object_test = MyObject()
    device2.object_test.list_test = ['asdf', 'qwer', 'asdfqwer']

    assert find_entity_field([device.to_dict(), device2.to_dict()], 'object_test') == [
        {'list_test': ['asdf', 'qwer', 'asdfqwer'], 'test': 'asdf'}, {'list_test': ['asdf', 'qwer', 'asdfqwer']}]


def test_merge_list_logic():
    device = MyDeviceAdapter(set(), set())
    device.object_test = MyObject()
    device.object_test.test = 'asdf'

    device2 = MyDeviceAdapter(set(), set())
    device2.object_test = MyObject()
    device2.object_test.list_test = ['asdf', 'qwer', 'asdfqwer']

    device3 = MyDeviceAdapter(set(), set())
    device3.object_test = MyObject()
    device3.object_test.list_test = ['asdf4', 'qwer', 'asdfqwer']

    device4 = MyDeviceAdapter(set(), set())
    device4.object_test = MyObject()
    device4.object_test.test = ''

    device5 = MyDeviceAdapter(set(), set())
    device5.object_test = MyObject()
    device5.object_test.test = 'asdf'
    device5.object_test.list_test = ['asdf', 'qwer', 'asdfqwer']

    fields = ['object_test.list_test', 'object_test.test']
    result = merge_entities_fields(
        list(map(lambda x: x.to_dict(), [device, device2, device3, device4, device5])), fields)
    assert result == [{'object_test.list_test': ['asdf4', 'asdfqwer', 'qwer']},
                      {'object_test.list_test': ['asdf', 'asdfqwer', 'qwer'], 'object_test.test': 'asdf'}]

    device = MyDeviceAdapter(set(), set())
    device.object_test = MyObject()
    device.object_test.list_test = ['a', 'b']

    device2 = MyDeviceAdapter(set(), set())
    device2.object_test = MyObject()
    device2.object_test.list_test = ['a']
    result = merge_entities_fields(
        list(map(lambda x: x.to_dict(), [device2, device])), fields)
    assert result == [{'object_test.list_test': ['a', 'b']}]
    result = merge_entities_fields(
        list(map(lambda x: x.to_dict(), [device, device2])), fields)
    assert result == [{'object_test.list_test': ['a', 'b']}]

    device = MyDeviceAdapter(set(), set())
    device.object_test = MyObject()
    device.object_test.list_test = ['a']

    device2 = MyDeviceAdapter(set(), set())
    device2.object_test = MyObject()
    device2.object_test.list_test = ['a']
    result = merge_entities_fields(
        list(map(lambda x: x.to_dict(), [device2, device])), fields)
    assert result == [{'object_test.list_test': ['a']}]

    device1 = MyDeviceAdapter(set(), set())
    device1.object_test = MyObject()
    device1.object_test.list_test = ['b', 'a', 'c']

    device2 = MyDeviceAdapter(set(), set())
    device2.object_test = MyObject()
    device2.object_test.list_test = ['b', 'c', 'a']
    result = merge_entities_fields(
        list(map(lambda x: x.to_dict(), [device2, device1])), fields)
    assert result == [{'object_test.list_test': ['a', 'b', 'c']}]


def test_hostname_obj():
    device = MyDeviceAdapter(set(), set())
    device.object_test = MyObject()
    device.object_test.hostname = 'cisco-switch'

    device2 = MyDeviceAdapter(set(), set())
    device2.object_test = MyObject()
    device2.object_test.hostname = 'cisco-switch.axonius.lan'

    assert parse_entity_fields([device.to_dict(), device2.to_dict()],
                               ['object_test.hostname']) == {'object_test.hostname': ['cisco-switch']}


def test_merge_speed():
    device = MyDeviceAdapter(set(), set())

    for i in range(1000):
        device.connected_hardware.append(DeviceAdapterConnectedHardware(name=f'asdf{i}', manufacturer=f'qwer{i}'))

    device2 = MyDeviceAdapter(set(), set())

    for i in range(1000):
        device2.connected_hardware.append(DeviceAdapterConnectedHardware(name=f'asdf{i}'))
    for i in range(1000):
        device2.connected_hardware.append(DeviceAdapterConnectedHardware(name=f'asdf{i}', manufacturer=f'zxcv{i}'))

    start = time.time()
    result = merge_entities_fields([device.to_dict(), device2.to_dict()],
                                   ['connected_hardware.name', 'connected_hardware.manufacturer'])
    end = time.time()
    assert len(result) == 2
    assert len(result[0]['connected_hardware.name']) == 1000
    assert end - start < 10

    devices = []
    for _ in range(10):
        device = MyDeviceAdapter(set(), set())

        for i in range(800):
            device.connected_hardware.append(DeviceAdapterConnectedHardware(name=f'asdf{i}', manufacturer=f'qwer{i}'))
        devices.append(device)

    start = time.time()
    result = merge_entities_fields([device.to_dict() for device in devices],
                                   ['connected_hardware.name', 'connected_hardware.manufacturer'])
    end = time.time()
    assert end - start < 10
