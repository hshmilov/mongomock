import pytest
from services.axonius_service import get_service
from test_credentials.test_gui_credentials import DEFAULT_USER
from test_helpers.device_helper import get_device_dict, filter_by_plugin_name

GUI_TEST_PLUGIN = 'GUI_TEST_PLUGIN'


def test_devices():
    axonius_system = get_service()
    gui_service = axonius_system.gui
    gui_service.login_user(DEFAULT_USER)

    for x in [4, 5, 6]:
        axonius_system.insert_device(get_device_dict("GUI_TEST", str(x), GUI_TEST_PLUGIN, "GUI_TEST_PLUGIN_1"))

    devices_response = gui_service.get_devices()
    assert devices_response.status_code == 200, f"Error in response. got response: {str(devices_response)}, " \
                                                f"{devices_response.content}"

    devices_count_response = gui_service.get_devices_count()
    assert devices_count_response.status_code == 200, f"Error in response. Got: {str(devices_count_response)}, " \
                                                      f"{devices_count_response.content}"
    assert isinstance(devices_count_response.json(), int), f"Unexpected response type: {devices_count_response.json()}"


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
        axonius_system.insert_device(get_device_dict("GUI_TEST", str(x), GUI_TEST_PLUGIN, "GUI_TEST_PLUGIN_1"))

    def get_gui_test_devices():
        devices_response = gui_service.get_devices()
        assert devices_response.status_code == 200, f"Error in response. got response: {str(devices_response)}, " \
                                                    f"{devices_response.content}"

        label_test_device = filter_by_plugin_name(devices_response.json(), GUI_TEST_PLUGIN)
        return label_test_device

    def create_label():
        def create_one_label():
            label_test_device = get_gui_test_devices()[0]

            starting_num_of_labels_on_device = _count_num_of_labels(label_test_device)
            test_label_value = 'test_create_label'
            result = gui_service.add_labels_to_device(
                {'entities': [label_test_device['internal_axon_id']], 'labels': [test_label_value]})
            assert result.status_code == 200, f"Failed adding label. reason: " \
                                              f"{str(result.status_code)}, {str(result.content)}"
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


if __name__ == '__main__':
    pytest.main([__file__])
