from services.gui_service import gui_fixture
from services.ad_service import ad_fixture
from test_helpers import utils


def test_plugin_is_up(axonius_fixture, gui_fixture):
    print("GUI is up")


def _count_num_of_tags(device):
    return len([current_tag['tagvalue'] for current_tag in device['tags'] if
                current_tag.get('tagvalue', '') != ''])


def test_tags(axonius_fixture, gui_fixture, ad_fixture):
    def create_tag():
        def create_one_tag():
            tag_test_device = gui_fixture.get_devices().json()[0]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tag_value = 'test_create_tag'
            gui_fixture.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            fresh_device = gui_fixture.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 1
            assert fresh_device['tags'][-1]['tagvalue'] == test_tag_value
            gui_fixture.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})

        def create_existing_tag():
            tag_test_device = gui_fixture.get_devices().json()[1]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tag_value = 'another_test_create_tag'
            gui_fixture.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            fresh_device = gui_fixture.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 1
            assert fresh_device['tags'][-1]['tagvalue'] == test_tag_value
            response = gui_fixture.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            assert response.status_code == 200
            fresh_device = gui_fixture.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 1
            assert fresh_device['tags'][-1]['tagvalue'] == test_tag_value
            gui_fixture.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})

        def create_multiple_tags_on_one_device():
            tag_test_device = gui_fixture.get_devices().json()[2]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tags = ['testing_is_awesome', 'our_ci_is_the_shit']
            gui_fixture.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': test_tags})
            fresh_device = gui_fixture.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 2
            assert set([current_tag['tagvalue'] for current_tag in fresh_device['tags'][-2:]]) == set(test_tags)
            gui_fixture.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': test_tags})

        if len(gui_fixture.get_devices().json()) < 3:
            utils.populate_test_devices(axonius_fixture, ad_fixture)
        create_one_tag()
        create_existing_tag()
        create_multiple_tags_on_one_device()

    def remove_tag():
        def remove_one_tag():
            tag_test_device = gui_fixture.get_devices().json()[0]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tag_value = 'test_remove_tag'
            gui_fixture.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            fresh_device = gui_fixture.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 1
            gui_fixture.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            fresh_device = gui_fixture.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert len([current_tag['tagvalue'] for current_tag in fresh_device['tags'] if
                        current_tag['tagvalue'] != '']) == starting_num_of_tags_on_device

        def remove_non_existing_tag():
            tag_test_device = gui_fixture.get_devices().json()[1]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tag_value = 'another_remove_tag'
            gui_fixture.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': [test_tag_value]})
            fresh_device = gui_fixture.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 1
            gui_fixture.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': ['blah_tag']})
            fresh_device = gui_fixture.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert len([current_tag['tagvalue'] for current_tag in fresh_device['tags'] if
                        current_tag['tagvalue'] != '']) == starting_num_of_tags_on_device + 1

        def remove_multiple_tags():
            tag_test_device = gui_fixture.get_devices().json()[2]
            starting_num_of_tags_on_device = _count_num_of_tags(tag_test_device)
            test_tag_value = ['removing_tags_are awesome', 'our_ci_is_the_shit']
            gui_fixture.add_tags_to_device(tag_test_device['internal_axon_id'], {'tags': test_tag_value})
            fresh_device = gui_fixture.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert _count_num_of_tags(fresh_device) == starting_num_of_tags_on_device + 2
            gui_fixture.remove_tags_from_device(tag_test_device['internal_axon_id'], {'tags': test_tag_value})
            fresh_device = gui_fixture.get_device_by_id(tag_test_device['internal_axon_id']).json()
            assert len([current_tag['tagvalue'] for current_tag in fresh_device['tags'] if
                        current_tag['tagvalue'] != '']) == starting_num_of_tags_on_device

        remove_one_tag()
        remove_non_existing_tag()
        remove_multiple_tags()

    create_tag()
    remove_tag()


def test_restart(axonius_fixture, gui_fixture):
    axonius_fixture.restart_plugin(gui_fixture)
