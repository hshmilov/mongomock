import pytest
from services.axonius_service import get_service
from test_helpers.device_helper import get_device_dict, filter_by_plugin_name

GUI_TEST_PLUGIN = 'GUI_TEST_PLUGIN'


def test_devices():
    axonius_service = get_service()
    gui_service = axonius_service.gui

    for x in [4, 5, 6]:
        axonius_service.insert_device(get_device_dict("GUI_TEST", str(x), GUI_TEST_PLUGIN, "GUI_TEST_PLUGIN_1"))

    gui_service.login_default_user()
    devices_response = gui_service.get_devices()
    assert devices_response.status_code == 200, f"Error in response. got response: {str(devices_response)}, " \
                                                f"{devices_response.content}"
    devices_count_expected = len(devices_response.json())
    devices_count_response = gui_service.get_devices_count()
    assert devices_count_response.status_code == 200, f"Error in response. Got: {str(devices_count_response)}, " \
                                                      f"{devices_count_response.content}"
    assert devices_count_expected == devices_count_response.json(), "Unexpected response. Original device count is " \
                                                                    f" {devices_count_expected} but count returned {devices_count_response.json()}"


def _count_num_of_tags(device):
    return len([current_tag['tagvalue'] for current_tag in device['tags'] if
                current_tag.get('tagvalue', '') != ''])


def test_tags_via_gui():
    axonius_service = get_service()
    gui_service = axonius_service.gui
    gui_service.login_default_user()

    for x in [1, 2, 3]:
        axonius_service.insert_device(get_device_dict("GUI_TEST", str(x), GUI_TEST_PLUGIN, "GUI_TEST_PLUGIN_1"))

    def get_gui_test_devices():
        devices_response = gui_service.get_devices()
        assert devices_response.status_code == 200, f"Error in response. got response: {str(devices_response)}, " \
                                                    f"{devices_response.content}"

        tag_test_device = filter_by_plugin_name(devices_response.json(), GUI_TEST_PLUGIN)
        return tag_test_device

    def create_tag():
        def create_one_tag():
            tag_test_device = get_gui_test_devices()[0]

            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tag_value = 'test_create_tag'
            result = gui_service.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            assert result.status_code == 200, f"Failed adding tag. reason: " \
                                              f"{str(result.status_code)}, {str(result.content)}"
            fresh_device = gui_service.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 1
            assert fresh_device['tags'][-1]['tagvalue'] == test_tag_value
            gui_service.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})

        def create_existing_tag():
            tag_test_device = get_gui_test_devices()[1]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tag_value = 'another_test_create_tag'
            gui_service.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            fresh_device = gui_service.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 1
            assert fresh_device['tags'][-1]['tagvalue'] == test_tag_value
            response = gui_service.add_tags_to_device(tag_test_device['internal_axon_id'],
                                                      {'tags': [test_tag_value]})
            assert response.status_code == 200
            fresh_device = gui_service.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 1
            assert fresh_device['tags'][-1]['tagvalue'] == test_tag_value
            gui_service.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})

        def create_multiple_tags_on_one_device():
            tag_test_device = get_gui_test_devices()[2]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tags = ['testing_is_awesome', 'our_ci_cures_cancer']
            gui_service.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': test_tags})
            fresh_device = gui_service.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 2
            assert set([current_tag['tagvalue'] for current_tag in fresh_device['tags'][-2:]]) == set(test_tags)
            gui_service.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': test_tags})

        create_one_tag()
        create_existing_tag()
        create_multiple_tags_on_one_device()

    def remove_tag():
        def remove_one_tag():
            tag_test_device = get_gui_test_devices()[0]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tag_value = 'test_remove_tag'
            gui_service.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            fresh_device = gui_service.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 1
            gui_service.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            fresh_device = gui_service.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert len([current_tag['tagvalue'] for current_tag in fresh_device['tags'] if
                        current_tag['tagvalue'] != '']) == starting_num_of_tags_on_device

        def remove_non_existing_tag():
            tag_test_device = get_gui_test_devices()[1]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tag_value = 'another_remove_tag'
            gui_service.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            fresh_device = gui_service.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 1
            gui_service.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': ['blah_tag']})
            fresh_device = gui_service.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert len([current_tag['tagvalue'] for current_tag in fresh_device['tags'] if
                        current_tag['tagvalue'] != '']) == starting_num_of_tags_on_device + 1

        def remove_multiple_tags():
            tag_test_device = get_gui_test_devices()[2]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tag_value = ['removing_tags_are awesome', 'our_ci_cures_cancer']
            gui_service.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': test_tag_value})
            fresh_device = gui_service.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 2
            gui_service.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': test_tag_value})
            fresh_device = gui_service.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert len([current_tag['tagvalue'] for current_tag in fresh_device['tags'] if
                        current_tag['tagvalue'] != '']) == starting_num_of_tags_on_device

        remove_one_tag()
        remove_non_existing_tag()
        remove_multiple_tags()

    create_tag()
    remove_tag()


def test_login():
    axonius_service = get_service()
    gui_service = axonius_service.gui

    bad_credentials_1 = {**gui_service.default_user, 'user_name': 'admin1'}
    bad_credentials_2 = {**gui_service.default_user, 'password': 'admin1'}

    response = gui_service.login_user(bad_credentials_1)
    assert response.status_code == 401

    response = gui_service.login_user(bad_credentials_2)
    assert response.status_code == 401

    response = gui_service.get_devices()
    assert response.status_code == 401

    response = gui_service.login_default_user()
    assert response.status_code == 200


if __name__ == '__main__':
    pytest.main(["parallel_tests/test_gui.py"])
