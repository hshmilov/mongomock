#!/usr/bin/env python3

import time

from axonius.devices.device_adapter import (DeviceAdapter,
                                            DeviceAdapterConnectedHardware,
                                            Field, ListField)
from axonius.entities import EntityType
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.gui_helpers import (find_entity_field,
                                       parse_entity_fields, flatten_fields, get_generic_fields)

# pylint: disable=line-too-long
from axonius.utils.merge_data import merge_entities_fields


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


# pylint:disable=too-many-statements
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

    fields = {'object_test.list_test': {'name': 'object_test.list_test', 'type': 'array'},
              'object_test.test': {'name': 'object_test.test', 'type': 'string'}}
    result = merge_entities_fields(
        list(map(lambda x: x.to_dict(), [device, device2, device3, device4, device5])), fields)
    assert result == [{'object_test.list_test': ['asdf', 'qwer', 'asdfqwer'], 'object_test.test': 'asdf'},
                      {'object_test.list_test': ['asdf', 'qwer', 'asdfqwer'], 'object_test.test': 'asdf'},
                      {'object_test.list_test': ['asdf4', 'qwer', 'asdfqwer']}]

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
    assert result == [{'object_test.list_test': ['b', 'a', 'c']}]

    # device: Eset.Axonius.Lan
    entities = [{'adapters': ['cisco_adapter'], 'mac': '00:50:56:91:A6:6B', 'manufacturer': '(VMware, Inc.)'},
                {'adapters': ['eset_adapter'], 'ips': ['192.168.20.52'], 'ips_v4': ['192.168.20.52'],
                 'mac': '00:50:56:91:A6:6B', 'manufacturer': '(VMware, Inc.)'},
                {'adapters': ['esx_adapter'], 'ips': ['192.168.20.52', 'fe80::250:56ff:fe91:a66b'],
                 'ips_v4': ['192.168.20.52'], 'ips_v6': ['fe80::250:56ff:fe91:a66b'], 'mac': '00:50:56:91:A6:6B',
                 'manufacturer': '(VMware, Inc.)'},
                {'adapters': ['nexpose_adapter'], 'ips': ['192.168.20.18'], 'ips_v4': ['192.168.20.18'],
                 'mac': '00:50:56:91:A6:6B', 'manufacturer': '(VMware, Inc.)'}
                ]

    fields = next(flatten_fields(field['items']) for field in get_generic_fields(EntityType.Devices)['items']
                  if field['name'] == 'network_interfaces')

    field_by_name = {
        field['name']: field for field in fields
        if field.get('type') != 'array' or field.get('items').get('type') != 'array'
    }
    field_by_name = {'adapters': {'name': 'adapters', 'type': 'array', 'title': 'Adapter Connections',
                                  'items': {'format': 'logo', 'type': 'string'}}, **field_by_name}

    result = merge_entities_fields(entities, field_by_name)
    assert result == [{'adapters': ['cisco_adapter', 'eset_adapter', 'esx_adapter'], 'mac': '00:50:56:91:A6:6B',
                       'manufacturer': '(VMware, Inc.)', 'ips': ['192.168.20.52', 'fe80::250:56ff:fe91:a66b'],
                       'ips_v4': ['192.168.20.52'], 'ips_v6': ['fe80::250:56ff:fe91:a66b']},
                      {'adapters': ['nexpose_adapter'], 'mac': '00:50:56:91:A6:6B', 'manufacturer': '(VMware, Inc.)',
                       'ips': ['192.168.20.18'], 'ips_v4': ['192.168.20.18']}]

    # device: DC4
    entities = [{'adapters': ['esx_adapter'], 'mac':'00:0C:29:B6:DA:46', 'manufacturer':'(VMware, Inc.)'},
                {'adapters': ['solarwinds_orion_adapter', 'nexpose_adapter'], 'ips': ['192.168.20.17'],
                 'ips_v4': ['192.168.20.17'], 'mac':'00:0C:29:B6:DA:46', 'manufacturer':'(VMware, Inc.)'},
                {'adapters': ['active_directory_adapter'], 'ips': ['192.168.20.17'], 'ips_v4': ['192.168.20.17'],
                 'subnets': ['192.168.20.0/24']},
                {'adapters': ['esx_adapter'], 'mac':'00:50:56:91:21:B3', 'manufacturer':'(VMware, Inc.)'},
                {'adapters': ['crowd_strike_adapter'], 'ips': ['192.168.20.36'], 'ips_v4': ['192.168.20.36'],
                 'mac':'00:50:56:91:3A:EC', 'manufacturer':'(VMware, Inc.)'},
                {'adapters': ['crowd_strike_adapter'], 'ips': ['192.168.20.58'], 'ips_v4': ['192.168.20.58'],
                 'mac':'00:50:56:91:DE:BB', 'manufacturer':'(VMware, Inc.)'},
                {'adapters': ['esx_adapter'], 'ips': ['fe80::2dba:9118:1fc8:7759', '192.168.20.58'],
                 'ips_v4': ['192.168.20.58'], 'ips_v6': ['fe80::2dba:9118:1fc8:7759'], 'mac':'00:50:56:91:DE:BB',
                 'manufacturer':'(VMware, Inc.)'},
                {'adapters': ['crowd_strike_adapter'], 'ips': ['192.168.20.50'], 'ips_v4': ['192.168.20.50'],
                 'mac':'00:50:56:91:33:E2', 'manufacturer':'(VMware, Inc.)'},
                {'adapters': ['crowd_strike_adapter'], 'ips': ['192.168.20.61'], 'ips_v4': ['192.168.20.61'],
                 'mac':'00:50:56:91:21:B3', 'manufacturer':'(VMware, Inc.)'}]

    result = merge_entities_fields(entities, field_by_name)
    assert result == [{'adapters': ['active_directory_adapter'], 'ips': ['192.168.20.17'], 'ips_v4': ['192.168.20.17'],
                       'subnets': ['192.168.20.0/24']},
                      {'adapters': ['crowd_strike_adapter'], 'mac': '00:50:56:91:3A:EC',
                       'manufacturer': '(VMware, Inc.)', 'ips': ['192.168.20.36'], 'ips_v4': ['192.168.20.36']},
                      {'adapters': ['crowd_strike_adapter'], 'mac': '00:50:56:91:33:E2',
                       'manufacturer': '(VMware, Inc.)', 'ips': ['192.168.20.50'], 'ips_v4': ['192.168.20.50']},
                      {'adapters': ['crowd_strike_adapter', 'esx_adapter'], 'mac': '00:50:56:91:21:B3',
                       'manufacturer': '(VMware, Inc.)', 'ips': ['192.168.20.61'], 'ips_v4': ['192.168.20.61']},
                      {'adapters': ['crowd_strike_adapter', 'esx_adapter'], 'mac': '00:50:56:91:DE:BB',
                       'manufacturer': '(VMware, Inc.)', 'ips': ['fe80::2dba:9118:1fc8:7759', '192.168.20.58'],
                       'ips_v4': ['192.168.20.58'], 'ips_v6': ['fe80::2dba:9118:1fc8:7759']},
                      {'adapters': ['esx_adapter', 'nexpose_adapter', 'solarwinds_orion_adapter'],
                       'mac': '00:0C:29:B6:DA:46', 'manufacturer': '(VMware, Inc.)', 'ips': ['192.168.20.17'],
                       'ips_v4': ['192.168.20.17']}]


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
    fields = {'connected_hardware.name': {'name': 'connected_hardware.name', 'type': 'array'},
              'connected_hardware.manufacturer': {'name': 'connected_hardware.manufacturer', 'type': 'array'}}
    result = merge_entities_fields([device.to_dict(), device2.to_dict()], fields)
    end = time.time()
    assert len(result) == 2
    assert len(result[0]['connected_hardware.name']) == 1000
    assert end - start < 12

    devices = []
    for _ in range(10):
        device = MyDeviceAdapter(set(), set())

        for i in range(800):
            device.connected_hardware.append(DeviceAdapterConnectedHardware(name=f'asdf{i}', manufacturer=f'qwer{i}'))
        devices.append(device)

    start = time.time()
    result = merge_entities_fields([device.to_dict() for device in devices], fields)
    end = time.time()
    assert end - start < 10
