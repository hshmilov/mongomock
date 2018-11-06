import pytest

from axonius.smart_json_class import SmartJsonClass, Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter


def create_smart_json_class():
    class MyDeviceTest(SmartJsonClass):
        name = Field(str, 'name')
        hostname = Field(str, 'hostname')
        tags = ListField(str, 'tags')

    return MyDeviceTest()


def test_regular_usage():
    device = create_smart_json_class()
    device.hostname = 'WIN7-JXN2L'
    assert device.hostname == 'WIN7-JXN2L'
    assert {'hostname': 'WIN7-JXN2L'} == device.to_dict()

    device['name'] = 'Test Windows 7'
    assert device['name'] == 'Test Windows 7'
    assert {'name': 'Test Windows 7', 'hostname': 'WIN7-JXN2L'} == device.to_dict()

    device.tags = ['ab', 'cd']
    assert {'name': 'Test Windows 7', 'hostname': 'WIN7-JXN2L', 'tags': ['ab', 'cd']} == device.to_dict()
    assert {
        'items':
            [
                {'name': 'name', 'title': 'name', 'type': 'string'},
                {'name': 'hostname', 'title': 'hostname', 'type': 'string'},
                {'name': 'tags', 'title': 'tags', 'items': {'type': 'string'}, 'type': 'array'}],
        'type': 'array'
    } == device.get_fields_info()


@pytest.mark.skip('TODO: add advance fields usage tests: AX-2393')
def test_advance_fields_usage():
    pass


def test_dynamic_fields():
    device = create_smart_json_class()
    device.declare_new_field('last_used_user', Field(str, 'Last Used User'))
    assert \
        {
            'name': 'last_used_user',
            'title': 'Last Used User',
            'type': 'string',
            'dynamic': True
        } in device.get_fields_info()['items']

    device.declare_new_field('hds', ListField(str, 'hds'))

    device['last_used_user'] = 'Avidor'
    assert device['last_used_user'] == 'Avidor'
    device.hds = ['c:\\', 'd:\\']
    device.hostname = 'AVIDOR-PC'
    assert {'last_used_user': 'Avidor', 'hostname': 'AVIDOR-PC', 'hds': ['c:\\', 'd:\\']} == device.to_dict()


def test_field_del():
    device = create_smart_json_class()
    device.declare_new_field('last_used_user', Field(str, 'Last Used User'))

    device.last_used_user = 'Avidor'
    device.hostname = 'AVIDOR-PC'
    device.last_used_user = None

    assert {'hostname': 'AVIDOR-PC'} == device.to_dict()


def test_str_auto_convert():
    device = create_smart_json_class()
    # If we put a list with one str, it should just get the str
    device.hostname = ['abcd']
    assert {'hostname': 'abcd'} == device.to_dict()

    # Otherwise anything else just goes through an str() function
    device.hostname = [5]
    assert {'hostname': '[5]'} == device.to_dict()
    device.hostname = 5
    assert {'hostname': '5'} == device.to_dict()
    device.hostname = ['abcd', 'efgh']
    assert {'hostname': '[\'abcd\', \'efgh\']'}


def test_inheritance_override():
    with pytest.raises(AssertionError) as e:
        class MyDeviceTest(SmartJsonClass):
            hostname1 = Field(str, 'Hostname')
            hostname2 = Field(str, 'Hostname')
    assert 'Found duplicate field titles' in str(e.value)

    with pytest.raises(AssertionError) as e:
        class MyDeviceParent1(SmartJsonClass):
            hostname = Field(str, 'Hostname1')

        class MyDeviceSon1(MyDeviceParent1):
            hostname = Field(str, 'Hostname2')

    assert 'SmartJsonClass same-name definition!' in str(e.value)

    with pytest.raises(AssertionError) as e:
        class MyDeviceParent2(SmartJsonClass):
            hostname1 = Field(str, 'Hostname')

        class MyDeviceSon2(MyDeviceParent2):
            hostname2 = Field(str, 'Hostname')

    assert 'SmartJsonClass same-title definition!' in str(e.value)

    # Now check with dynamic fields
    device = create_smart_json_class()
    with pytest.raises(AssertionError) as e:
        device.declare_new_field('hostname', Field(str, 'not a hostname'))

    assert 'field attr-name (field_name) already exists' in str(e.value)

    with pytest.raises(AssertionError) as e:
        device.declare_new_field('not_a_hostname', Field(str, 'hostname'))

    assert 'field gui-name (field.title) already exists' in str(e.value)


def test_fields_schema_change():
    class MyDeviceSchemaTests(SmartJsonClass):
        hostname = Field(str, 'hostname')

    device1 = MyDeviceSchemaTests()
    device2 = MyDeviceSchemaTests()

    device1.declare_new_field('hostname1', Field(str, 'hostname1'))
    device2.declare_new_field('hostname2', Field(str, 'hostname2'))

    assert [{'name': 'hostname', 'title': 'hostname', 'type': 'string'}] == device1.get_fields_info('static')['items']
    assert {'name': 'hostname1', 'title': 'hostname1', 'type': 'string', 'dynamic': True} in device1.get_fields_info()[
        'items']
    assert {'name': 'hostname2', 'title': 'hostname2', 'type': 'string', 'dynamic': True} in device1.get_fields_info()[
        'items']


def test_schema_changes_with_widely_used_classes():
    # DeviceAdapter and UserAdapter do not have their own schema representation in the gui since they are 'generic'.
    #  so the gui takes them directly (gui_helpers.py::entity_fields). So we can not change them.
    device = DeviceAdapter({}, {})
    with pytest.raises(AssertionError) as e:
        device.declare_new_field('new_field', Field(str, 'New Field'))

    assert 'Can not change DeviceAdapter, its generic!' in str(e.value)

    user = UserAdapter({}, {})
    with pytest.raises(AssertionError) as e:
        user.declare_new_field('new_field', Field(str, 'New Field'))

    assert 'Can not change UserAdapter, its generic!' in str(e.value)

    class DeviceAdapterSon(DeviceAdapter):
        new_field = Field(str, 'New Field')

    device = DeviceAdapterSon({}, {})
    device.declare_new_field('new_field_2', Field(str, 'New Field 2'))
    assert {'name': 'new_field', 'title': 'New Field', 'type': 'string'} in device.get_fields_info()['items']
    assert \
        {
            'name': 'new_field_2',
            'title': 'New Field 2',
            'type': 'string',
            'dynamic': True
        } in device.get_fields_info()['items']
    assert \
        [
            {
                'name': 'new_field_2',
                'title': 'New Field 2',
                'type': 'string',
                'dynamic': True
            }
        ] == device.get_fields_info('dynamic')['items']
