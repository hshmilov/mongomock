import random
import uuid

import pytest

from test_helpers.device_helper import get_entity_axonius_dict_multiadapter
from services.axonius_service import get_service
from test_credentials.test_gui_credentials import DEFAULT_USER
from test_helpers.device_helper import get_entity_axonius_dict, filter_by_plugin_name
from test_helpers.user_helper import get_user_dict
from test_helpers.report_helper import get_alert_dict, create_alert_dict

pytestmark = pytest.mark.sanity

GUI_TEST_PLUGIN = 'GUI_TEST_PLUGIN'
API_TOKEN = (DEFAULT_USER['user_name'], DEFAULT_USER['password'])


def test_devices():
    axonius_system = get_service()
    gui_service = axonius_system.gui
    gui_service.login_user(DEFAULT_USER)

    for x in [4, 5, 6]:
        axonius_system.insert_device(get_entity_axonius_dict('GUI_TEST', str(x), GUI_TEST_PLUGIN, 'GUI_TEST_PLUGIN_1'))

    devices_response = gui_service.get_devices()
    assert devices_response.status_code == 200, f'Error in response. got response: {str(devices_response)}, ' \
                                                f'{devices_response.content}'

    devices_count_response = gui_service.get_devices_count()
    assert devices_count_response.status_code == 200, f'Error in response. Got: {str(devices_count_response)}, ' \
                                                      f'{devices_count_response.content}'
    assert isinstance(devices_count_response.json(), int), f'Unexpected response type: {devices_count_response.json()}'


def _count_num_of_labels(device):
    return len(device['labels'])


def test_default_views():
    axonius_system = get_service()
    gui_service = axonius_system.gui

    assert gui_service.is_up()  # default views are inserted when the GUI service is starting, make sure it is up...
    views = axonius_system.db.get_collection(gui_service.unique_name, 'device_views')

    # A sample Default View as set in default_views_devices.ini under gui/src
    name = 'AD Printers'

    existed_query = views.find_one({'name': name})
    assert existed_query is not None


def test_labels_via_gui():
    axonius_system = get_service()
    gui_service = axonius_system.gui
    gui_service.login_user(DEFAULT_USER)

    for x in [1, 2, 3]:
        axonius_system.insert_device(get_entity_axonius_dict('GUI_TEST', str(x), GUI_TEST_PLUGIN, 'GUI_TEST_PLUGIN_1'))

    def get_gui_test_devices():
        devices_response = gui_service.get_devices()
        assert devices_response.status_code == 200, f'Error in response. got response: {str(devices_response)}, ' \
                                                    f'{devices_response.content}'

        label_test_device = filter_by_plugin_name(devices_response.json(), GUI_TEST_PLUGIN)
        return label_test_device

    def create_label():
        def create_one_label():
            label_test_device = get_gui_test_devices()[0]

            starting_num_of_labels_on_device = _count_num_of_labels(label_test_device)
            test_label_value = 'test_create_label'
            result = gui_service.add_labels_to_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': [test_label_value]})
            assert result.status_code == 200, f'Failed adding label. reason: ' \
                                              f'{str(result.status_code)}, {str(result.content)}'
            fresh_device = gui_service.get_device_by_id(label_test_device['internal_axon_id']).json()

            # TODO: fix the following race condition
            # If the next asserts fail, it might be because of a raise condition. did someone add label meanwhile?
            assert _count_num_of_labels(fresh_device) == starting_num_of_labels_on_device + 1
            assert fresh_device['labels'][-1] == test_label_value
            gui_service.remove_labels_from_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': [test_label_value]})

        def create_existing_labels():
            label_test_device = get_gui_test_devices()[1]
            starting_num_of_labels_on_device = _count_num_of_labels(label_test_device)
            test_label_value = 'another_test_create_label'
            gui_service.add_labels_to_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': [test_label_value]})
            fresh_device = gui_service.get_device_by_id(label_test_device['internal_axon_id']).json()

            # TODO: fix the following race condition
            # If the next asserts fail, it might be because of a raise condition. did someone add label meanwhile?
            assert _count_num_of_labels(fresh_device) == starting_num_of_labels_on_device + 1
            assert fresh_device['labels'][-1] == test_label_value
            response = gui_service.add_labels_to_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': [test_label_value]})
            assert response.status_code == 200
            fresh_device = gui_service.get_device_by_id(label_test_device['internal_axon_id']).json()
            assert _count_num_of_labels(fresh_device) == starting_num_of_labels_on_device + 1
            assert fresh_device['labels'][-1] == test_label_value
            gui_service.remove_labels_from_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': [test_label_value]})

        def create_multiple_labels_on_one_device():
            label_test_device = get_gui_test_devices()[2]
            starting_num_of_labels_on_device = _count_num_of_labels(label_test_device)
            test_labels = ['testing_is_awesome', 'our_ci_cures_cancer']
            gui_service.add_labels_to_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': test_labels})
            fresh_device = gui_service.get_device_by_id(label_test_device['internal_axon_id']).json()

            # TODO: fix the following race condition
            # If the next asserts fail, it might be because of a raise condition. did someone add label meanwhile?
            assert _count_num_of_labels(fresh_device) == starting_num_of_labels_on_device + 2
            assert set([current_label for current_label in fresh_device['labels'][-2:]]) == set(test_labels)
            gui_service.remove_labels_from_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': test_labels})

        create_one_label()
        create_existing_labels()
        create_multiple_labels_on_one_device()

    def remove_label():
        def remove_one_label():
            label_test_device = get_gui_test_devices()[0]
            starting_num_of_labels_on_device = _count_num_of_labels(label_test_device)
            test_label_value = 'test_remove_label'

            # TODO: fix the following race condition
            # If the next asserts fail, it might be because of a raise condition. did someone add label meanwhile?

            gui_service.add_labels_to_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': [test_label_value]})
            fresh_device = gui_service.get_device_by_id(label_test_device['internal_axon_id']).json()
            assert _count_num_of_labels(fresh_device) == starting_num_of_labels_on_device + 1

            gui_service.remove_labels_from_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': [test_label_value]})
            fresh_device = gui_service.get_device_by_id(label_test_device['internal_axon_id']).json()
            assert _count_num_of_labels(fresh_device) == starting_num_of_labels_on_device

        def remove_non_existing_label():
            label_test_device = get_gui_test_devices()[1]
            starting_num_of_labels_on_device = _count_num_of_labels(label_test_device)
            test_label_value = 'another_remove_label'

            # TODO: fix the following race condition
            # If the next asserts fail, it might be because of a raise condition. did someone add label meanwhile?

            gui_service.add_labels_to_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': [test_label_value]})
            fresh_device = gui_service.get_device_by_id(label_test_device['internal_axon_id']).json()
            assert _count_num_of_labels(fresh_device) == starting_num_of_labels_on_device + 1
            gui_service.remove_labels_from_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': ['blah_label']})
            fresh_device = gui_service.get_device_by_id(label_test_device['internal_axon_id']).json()
            assert len(fresh_device['labels']) == starting_num_of_labels_on_device + 1

        def remove_multiple_labels():
            label_test_device = get_gui_test_devices()[2]
            starting_num_of_labels_on_device = _count_num_of_labels(label_test_device)
            test_labels_values = ['removing_labels_are awesome', 'our_ci_cures_cancer']

            # TODO: fix the following race condition
            # If the next asserts fail, it might be because of a raise condition. did someone add label meanwhile?

            gui_service.add_labels_to_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': test_labels_values})
            fresh_device = gui_service.get_device_by_id(label_test_device['internal_axon_id']).json()

            assert _count_num_of_labels(fresh_device) == starting_num_of_labels_on_device + 2
            gui_service.remove_labels_from_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': test_labels_values})
            fresh_device = gui_service.get_device_by_id(label_test_device['internal_axon_id']).json()
            assert len(fresh_device['labels']) == starting_num_of_labels_on_device

        remove_one_label()
        remove_non_existing_label()
        remove_multiple_labels()

    create_label()
    remove_label()


def test_login():
    axonius_system = get_service()
    gui_service = axonius_system.gui

    bad_credentials_1 = {**DEFAULT_USER, 'user_name': 'admin1'}
    bad_credentials_2 = {**DEFAULT_USER, 'password': 'admin1'}

    response = gui_service.login_user(bad_credentials_1)
    assert response.status_code == 401

    response = gui_service.login_user(bad_credentials_2)
    assert response.status_code == 401

    response = gui_service.get_devices()
    assert response.status_code == 401

    response = gui_service.login_user(DEFAULT_USER)
    assert response.status_code == 200


def test_maintenance_endpoints():
    axonius_system = get_service()
    gui_service = axonius_system.gui

    assert gui_service.anaylitics().strip() == b'true'
    assert gui_service.troubleshooting().strip() == b'true'


def test_deleting_devices():
    '''
    This tests the feature that allows the user to delete devices
    '''
    axonius_system = get_service()

    gui_service = axonius_system.gui
    gui_service.login_user(DEFAULT_USER)

    adapter_tested = ['some_adapter', 'some_adapter_123']  # plugin_name, plugin_unique_name
    some_id = uuid.uuid4().hex
    axon_device = get_entity_axonius_dict_multiadapter('GUI_TEST', [[uuid.uuid4().hex, *adapter_tested, some_id]])
    axonius_system.insert_device(axon_device)

    def get_device_by_internal_axon_id(internal_axon_id):
        return gui_service.get_devices(params={'filter': f'internal_axon_id == \'{internal_axon_id}\''}).json()

    devices_response = get_device_by_internal_axon_id(axon_device['internal_axon_id'])[0]
    assert set(devices_response['adapters']) == {'some_adapter'}

    assert gui_service.delete_devices([axon_device['internal_axon_id']]).status_code == 200
    devices_response = get_device_by_internal_axon_id(axon_device['internal_axon_id'])
    assert len(devices_response) == 0


def test_deleting_users():
    '''
    This tests the feature that allows the user to delete users
    '''
    axonius_system = get_service()

    gui_service = axonius_system.gui
    gui_service.login_user(DEFAULT_USER)

    adapter_tested = ['some_adapter', 'some_adapter_123']  # plugin_name, plugin_unique_name
    some_id = uuid.uuid4().hex

    axon_device = get_entity_axonius_dict_multiadapter('GUI_TEST', [[uuid.uuid4().hex, *adapter_tested, some_id]])
    axonius_system.insert_user(axon_device)

    def get_user_by_internal_axon_id(internal_axon_id):
        return gui_service.get_users(params={'filter': f'internal_axon_id == \'{internal_axon_id}\''}).json()

    users_response = get_user_by_internal_axon_id(axon_device['internal_axon_id'])[0]
    assert set(users_response['adapters']) == {'some_adapter'}

    assert gui_service.delete_users([axon_device['internal_axon_id']]).status_code == 200
    users_response = get_user_by_internal_axon_id(axon_device['internal_axon_id'])
    assert len(users_response) == 0


#######
# API #
#######

def test_api_devices():
    def test_get_all_devices():
        axonius_system = get_service()
        gui_service = axonius_system.gui

        for x in [4, 5, 6]:
            axonius_system.insert_device(
                get_entity_axonius_dict('GUI_TEST', str(x), GUI_TEST_PLUGIN, 'GUI_TEST_PLUGIN_2'))

        devices_response = gui_service.get_api_devices(auth=API_TOKEN)
        assert devices_response.status_code == 200, f'Error in response. got response: {str(devices_response)}, ' \
                                                    f'{devices_response.content}'

        devices_count_response = gui_service.get_devices_count()
        assert devices_count_response.status_code == 200, f'Error in response. Got: {str(devices_count_response)}, ' \
                                                          f'{devices_count_response.content}'

        assert int(devices_count_response.content) == len(
            devices_response.json()), f'Error in device count . Got: {str(len(devices_response.json()))}, ' \
                                      f'{devices_count_response.content}'
        assert isinstance(devices_count_response.json(),
                          int), f'Unexpected response type: {devices_count_response.json()}'

        def test_get_specific_device():
            axonius_system = get_service()
            gui_service = axonius_system.gui
            random_id = random.randint(50, 1000)
            device_to_get = get_entity_axonius_dict('GUI_TEST', str(random_id), GUI_TEST_PLUGIN, 'GUI_TEST_PLUGIN_3')

            axonius_system.insert_device(device_to_get)

            device_response = gui_service.get_api_device_by_id(device_to_get['internal_axon_id'], auth=API_TOKEN)
            assert device_response.status_code == 200, f'Error in response. got response: {str(devices_response)}, ' \
                                                       f'{devices_response.content}'

            assert device_response.json() == device_to_get, f'Error brought bad device by id. Got: {str(devices_response.json())}, ' \
                                                            f'{device_to_get}'

        test_get_all_devices()
        test_get_specific_device()


@pytest.mark.skip("AX-1901")
def test_api_users():
    def test_get_all_users():
        axonius_system = get_service()
        gui_service = axonius_system.gui

        for x in [4, 5, 6]:
            # insert_device(get_entity_axonius_dict('GUI_TEST', str(x), GUI_TEST_PLUGIN, 'GUI_TEST_PLUGIN_2'))
            axonius_system.insert_user(get_user_dict('GUI_TEST', str(x), GUI_TEST_PLUGIN, 'GUI_TEST_PLUGIN_2'))

        users_response = gui_service.get_api_users(auth=API_TOKEN)
        assert users_response.status_code == 200, f'Error in response. got response: {str(users_response)}, ' \
                                                  f'{users_response.content}'

        gui_service.login_user(DEFAULT_USER)
        users_count_response = gui_service.get_users_count()
        assert users_count_response.status_code == 200, f'Error in response. Got: {str(users_count_response)}, ' \
                                                        f'{users_count_response.content}'

        assert isinstance(users_count_response.json(),
                          int), f'Unexpected response type: {users_count_response.json()}'

        assert users_count_response.json() == len(
            users_response.json()['assets']), f"Error in device count. Got: {str(len(users_response.json()))}, " \
                                              f"{users_count_response.json()}"

    def test_get_specific_user():
        axonius_system = get_service()
        gui_service = axonius_system.gui
        random_id = random.randint(50, 1000)
        user_to_get = get_user_dict('GUI_TEST', str(random_id), GUI_TEST_PLUGIN, 'GUI_TEST_PLUGIN_3')

        axonius_system.insert_user(user_to_get)

        user_response = gui_service.get_api_user_by_id(user_to_get['internal_axon_id'], auth=API_TOKEN)
        assert user_response.status_code == 200, f'Error in response. got response: {str(user_response)}, ' \
                                                 f'{user_response.content}'

    test_get_all_users()
    test_get_specific_user()


def test_api_alerts():
    def test_get_all_alerts():
        axonius_system = get_service()
        gui_service = axonius_system.gui

        for x in [4, 5, 6]:
            axonius_system.insert_report(get_alert_dict(f'GUI_TEST_QUERY{x}', f'GUI_TEST_REPORT_{x}'))

        alert_response = gui_service.get_api_reports(auth=API_TOKEN)
        assert alert_response.status_code == 200, f'Error in response. got response: {str(alert_response)}, ' \
                                                  f'{alert_response.content}'

    def test_get_specific_alert():
        axonius_system = get_service()
        gui_service = axonius_system.gui
        alert_to_get = get_alert_dict('GUI_TEST_QUERY_1', 'GUI_TEST_REPORT_1')

        axonius_system.insert_report(alert_to_get)

        alert_response = gui_service.get_api_report_by_id(str(alert_to_get['_id']), auth=API_TOKEN)
        assert alert_response.status_code == 200, f'Error in response. got response: {str(alert_response)}, ' \
                                                  f'{alert_response.content}'

        assert alert_response.json() == alert_to_get, f'Error brought bad device by id. Got: {str(alert_response.json())}, ' \
                                                      f'{alert_to_get}'

    def test_create_alert():
        axonius_system = get_service()
        gui_service = axonius_system.gui
        alert_to_put = create_alert_dict('AD Printers', 'GUI_TEST_REPORT_1')

        alert_response = gui_service.put_api_report(alert_to_put, auth=API_TOKEN)
        assert alert_response.status_code == 201, f'Error in response. got response: {str(alert_response)}, ' \
                                                  f'{alert_response.content}'

        alert_response = gui_service.get_api_report_by_id(str(alert_to_put), auth=API_TOKEN)
        assert alert_response.status_code == 200, f'Error in response. got response: {str(alert_response)}, ' \
                                                  f'{alert_response.content}'

        assert alert_response.json() == alert_to_put, f'Error brought bad device by id. Got: {str(alert_response.json())}, ' \
                                                      f'{alert_to_put}'

    def test_delete_alert():
        axonius_system = get_service()
        gui_service = axonius_system.gui
        alert_to_get = get_alert_dict('GUI_TEST_QUERY_1', 'GUI_TEST_REPORT_1')

        axonius_system.insert_report(alert_to_get)

        alert_response = gui_service.delete_api_report_by_id(str(alert_to_get['_id']), auth=API_TOKEN)
        assert alert_response.status_code == 200, f'Error in response. got response: {str(alert_response)}, ' \
                                                  f'{alert_response.content}'

        assert alert_response.json() == alert_to_get, f'Error brought bad device by id. Got: {str(alert_response.json())}, ' \
                                                      f'{alert_to_get}'

        test_get_all_alerts()
        test_get_specific_alert()
        test_create_alert()
        test_delete_alert()


def test_api_key_auth():
    """
    Test the API using API-Key auth instead of username and password
    """
    axonius_system = get_service()
    gui_service = axonius_system.gui
    gui_service.login_user(DEFAULT_USER)
    api_data = gui_service.get_api_key()
    gui_service.logout_user()
    gui_service.get_api_devices(headers={
        'api-key': api_data['api_key'],
        'api-secret': api_data['api_secret']
    }).raise_for_status()


if __name__ == '__main__':
    pytest.main([__file__])
