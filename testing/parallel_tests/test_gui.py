from services.axonius_service import get_service
from test_helpers.utils import try_until_not_thrown


def _count_num_of_tags(device):
    return len([current_tag['tagvalue'] for current_tag in device['tags'] if
                current_tag.get('tagvalue', '') != ''])


def test_tags_via_gui():
    axonius_service = get_service()
    gui_service = axonius_service.gui
    gui_service.login_default_user()

    # can't start the test until we have some devices aggregated
    # when parallel test run there are many adapters and we just wait for devices
    # if you want to run this test standalone - just populate db with some devices
    # It can be a good idea in the future to provide such a utility function
    def has_at_least_one_device():
        assert len(gui_service.get_devices().json()) > 2

    try_until_not_thrown(15, 5, has_at_least_one_device)

    def create_tag():
        def create_one_tag():
            devices_response = gui_service.get_devices()
            assert devices_response.status_code == 200, f"Error in response. got response: {str(devices_response)}, " \
                                                        f"{devices_response.content}"
            tag_test_device = devices_response.json()[0]

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
            tag_test_device = gui_service.get_devices().json()[1]
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
            tag_test_device = gui_service.get_devices().json()[2]
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
            tag_test_device = gui_service.get_devices().json()[0]
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
            tag_test_device = gui_service.get_devices().json()[1]
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
            tag_test_device = gui_service.get_devices().json()[2]
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

    response = gui_service.login_user(gui_service.default_user)
    assert response.status_code == 200
