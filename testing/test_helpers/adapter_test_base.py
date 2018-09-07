# pylint: disable=unused-import,no-name-in-module,ungrouped-imports
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from flaky import flaky

try:
    import axonius
except (ModuleNotFoundError, ImportError):
    # if not in path...
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'axonius-libs',
                                                 'src', 'libs', 'axonius-py')))
from axonius.plugin_base import EntityType
from services.axonius_service import get_service
from test_credentials.test_bad_credentials import FAKE_CLIENT_DETAILS
from test_credentials.test_gui_credentials import DEFAULT_USER
from test_helpers.device_helper import get_entity_axonius_dict_multiadapter
from test_helpers.utils import check_conf


class AdapterTestBase:
    """
    Basic tests for adapter are defined here.
    If one wants to skip or modify a test he can do that by overriding the corresponding method.
    If one wants to skip a test - he can do that by overriding and marking the test with @pytest.mark.skip
    """
    axonius_system = get_service()

    @property
    def adapter_service(self):
        raise NotImplementedError

    @property
    def adapter_name(self):
        return self.adapter_service.plugin_name

    @property
    def some_client_id(self):
        raise NotImplementedError

    @property
    def some_user_id(self):
        raise NotImplementedError

    @property
    def some_client_details(self):
        raise NotImplementedError

    @property
    def some_device_id(self):
        raise NotImplementedError

    @property
    def device_alive_thresh_last_seen(self):
        return self.adapter_service.get_configurable_config('AdapterBase')['last_seen_threshold_hours']

    @property
    def device_thresh_last_fetched(self):
        return self.adapter_service.get_configurable_config('AdapterBase')['last_fetched_threshold_hours']

    @property
    def user_alive_thresh_last_seen(self):
        return self.adapter_service.get_configurable_config('AdapterBase')['user_last_seen_threshold_hours']

    @property
    def user_alive_thresh_last_fetched(self):
        return self.adapter_service.get_configurable_config('AdapterBase')['user_last_fetched_threshold_hours']

    def set_minimum_time_until_next_fetch(self, value):
        return self.adapter_service.set_configurable_config('AdapterBase', 'minimum_time_until_next_fetch', value)

    def get_last_threshold(self, entity_type: EntityType):
        if entity_type == EntityType.Devices:
            return self.device_alive_thresh_last_seen, self.device_thresh_last_fetched
        if entity_type == EntityType.Users:
            return self.user_alive_thresh_last_seen, self.user_alive_thresh_last_fetched
        return None

    def drop_clients(self):
        self.axonius_system.db.client[self.adapter_service.unique_name].drop_collection('clients')

    def test_adapter_is_up(self):
        assert self.adapter_service.is_up()

    @pytest.mark.skip('Not all plugins have schemas - TODO: Figure out how to test this properly or delete')
    def test_adapter_responds_to_schema(self):
        assert self.adapter_service.schema().status_code == 200

    def test_adapter_in_configs(self):
        check_conf(self.axonius_system, self.adapter_service, self.adapter_name)

    def test_check_registration(self):
        assert self.adapter_service.is_plugin_registered(self.axonius_system.core)

    def test_check_reachability(self):
        assert self.adapter_service.is_client_reachable(self.some_client_details)
        assert not self.adapter_service.is_client_reachable(FAKE_CLIENT_DETAILS)

    @flaky(max_runs=2)
    def test_fetch_devices(self):
        self.adapter_service.add_client(self.some_client_details)
        self.axonius_system.assert_device_aggregated(
            self.adapter_service, [(self.some_client_id, self.some_device_id)])

    def test_fetch_users(self):
        try:
            # not all implement this
            user_id = self.some_user_id
        except NotImplementedError:
            return
        self.adapter_service.add_client(self.some_client_details)
        self.axonius_system.assert_user_aggregated(self.adapter_service, [(self.some_client_id, user_id)])

    def test_devices_cleaning(self):
        return self.do_test_entity_cleaning(EntityType.Devices)

    def test_users_cleaning(self):
        return self.do_test_entity_cleaning(EntityType.Users)

    def do_test_entity_cleaning(self, entity_type: EntityType):
        self.adapter_service.trigger_clean_db()  # first clean might not be empty
        cleaned_count = self.adapter_service.trigger_clean_db()[entity_type.value]
        assert cleaned_count == 0  # second clean should have no entities cleaned

        now = datetime.now(tz=timezone.utc)
        last_seen, last_fetched = self.get_last_threshold(entity_type)
        if last_seen:
            last_seen_long_time_ago = now - timedelta(hours=last_seen * 5)
        if last_fetched:
            last_fetched_long_time_ago = now - timedelta(hours=last_fetched * 5)

        entity_db = self.axonius_system.db.get_entity_db(entity_type)

        # this is a fake entity that is 'new' on all forms
        entity_db.insert_one({
            'internal_axon_id': '1-' + uuid.uuid4().hex,
            'accurate_for_datetime': now,
            'adapters': [
                {
                    'client_used': 'SomeClient',
                    'plugin_type': 'Adapter',
                    'plugin_name': self.adapter_service.plugin_name,
                    'plugin_unique_name': self.adapter_service.unique_name,
                    'accurate_for_datetime': now,
                    'data': {
                        'id': '2-' + uuid.uuid4().hex,
                        'raw': {
                        },
                    }
                }
            ],
            'tags': []
        })
        cleaned_count = self.adapter_service.trigger_clean_db()[entity_type.value]
        assert cleaned_count == 0  # the entity added shouldn't be removed

        if last_fetched:
            # this is a fake entity from a 'long time ago' by last_fetched
            deleted_entity_id = '3-' + uuid.uuid4().hex
            entity_db.insert_one({
                'internal_axon_id': deleted_entity_id,
                'accurate_for_datetime': now,
                'adapters': [
                    {
                        'client_used': 'SomeClient',
                        'plugin_type': 'Adapter',
                        'plugin_name': self.adapter_service.plugin_name,
                        'plugin_unique_name': self.adapter_service.unique_name,
                        'accurate_for_datetime': last_fetched_long_time_ago,
                        'data': {
                            'id': '4-' + uuid.uuid4().hex,
                            'raw': {
                            },
                        }
                    }
                ],
                'tags': []
            })
            cleaned_count = self.adapter_service.trigger_clean_db()[entity_type.value]
            assert cleaned_count == 1  # the entity added is old and should be deleted
            assert entity_db.count_documents({'internal_axon_id': deleted_entity_id}) == 0

            deleted_entity_id = '5-' + uuid.uuid4().hex
            deleted_adapter_entity_id = '6-' + uuid.uuid4().hex
            not_deleted_adapter_entity_id = '7-' + uuid.uuid4().hex
            entity_db.insert_one({
                'internal_axon_id': deleted_entity_id,
                'accurate_for_datetime': now,
                'adapters': [
                    {
                        'client_used': 'SomeClient',
                        'plugin_type': 'Adapter',
                        'plugin_name': self.adapter_service.plugin_name,
                        'plugin_unique_name': self.adapter_service.unique_name,
                        'accurate_for_datetime': last_fetched_long_time_ago,
                        'data': {
                            'id': deleted_adapter_entity_id,
                            'raw': {
                            },
                        }
                    },
                    {
                        'client_used': 'SomeClientFromAnotherAdapter',
                        'plugin_type': 'Adapter',
                        'plugin_name': 'high_capacity_carburetor_adapter',
                        'plugin_unique_name': 'high_capacity_carburetor_adapter_1337',
                        'accurate_for_datetime': now,
                        'data': {
                            'raw': {
                            },
                            'id': not_deleted_adapter_entity_id,
                        }
                    }
                ],
                'tags': []
            })

            cleaned_count = self.adapter_service.trigger_clean_db()[entity_type.value]
            assert cleaned_count == 1  # the entity added is old and should be deleted
            # only one of the adapter_entitys should be removed, so the axonius entity should stay
            assert entity_db.count_documents({'adapters.data.id': not_deleted_adapter_entity_id}) == 1
            # verify our entity is deleted
            assert entity_db.count_documents({'adapters.data.id': deleted_adapter_entity_id}) == 0

        if last_seen:
            # this is a fake entity from a 'long time ago' according to `last_seen`
            deleted_entity_id = '8-' + uuid.uuid4().hex
            entity_db.insert_one({
                'internal_axon_id': deleted_entity_id,
                'accurate_for_datetime': now,
                'adapters': [
                    {
                        'client_used': 'SomeClient',
                        'plugin_type': 'Adapter',
                        'plugin_name': self.adapter_service.plugin_name,
                        'plugin_unique_name': self.adapter_service.unique_name,
                        'accurate_for_datetime': now,
                        'data': {
                            'id': '9-' + uuid.uuid4().hex,
                            'last_seen': last_seen_long_time_ago,
                            'raw': {
                            },
                        }
                    }
                ],
                'tags': []
            })
            cleaned_count = self.adapter_service.trigger_clean_db()[entity_type.value]
            assert cleaned_count == 1
            assert entity_db.count_documents({'internal_axon_id': deleted_entity_id}) == 0

    def test_restart(self):
        service = self.adapter_service
        # it's ok to restart adapter in adapter test
        service.take_process_ownership()
        self.axonius_system.restart_plugin(service)

    def test_removing_adapter_creds_with_devices(self):
        """
        This tests the feature that allows the user to delete a set of credentials from an adapter
        and also deleting all associated devices to those credentials.
        """
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        out_client_id = self.some_client_id

        gui_service = self.axonius_system.gui
        gui_service.login_user(DEFAULT_USER)

        adapter_tested = [self.adapter_service.plugin_name, self.adapter_service.unique_name]
        not_our_adapter = ['lol_adapter', 'lol_adapter_321']

        axon_device = get_entity_axonius_dict_multiadapter('GUI_CLIENT_DELETE_TEST',
                                                           [[uuid.uuid4().hex, *adapter_tested, out_client_id],
                                                            [uuid.uuid4().hex, *not_our_adapter]])
        out_id = axon_device['adapters'][0]['data']['id']
        lol_id = axon_device['adapters'][1]['data']['id']
        self.axonius_system.insert_device(axon_device)

        def get_devices_by_id(adapter_name, data_id):
            res = gui_service.get_devices(params={
                'filter':
                    f'adapters_data.{adapter_name}.id == \'{data_id}\''}).json()
            return res

        devices_response = get_devices_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name, 'lol_adapter'}

        assert gui_service.delete_client(self.adapter_service.unique_name, our_client_object_id).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        out_client_id = self.some_client_id

        devices_response = get_devices_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name, 'lol_adapter'}

        devices_response = get_devices_by_id('lol_adapter', lol_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name, 'lol_adapter'}

        assert gui_service.delete_client(self.adapter_service.unique_name, our_client_object_id,
                                         params={
                                             'deleteEntities': 'True'
                                         }).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        out_client_id = self.some_client_id

        devices_response = get_devices_by_id('lol_adapter', lol_id)[0]
        assert set(devices_response['adapters']) == {'lol_adapter'}
        assert len(get_devices_by_id(self.adapter_service.plugin_name, out_id)) == 0

        # test without linked devices
        axon_device = get_entity_axonius_dict_multiadapter('GUI_CLIENT_DELETE_TEST',
                                                           [[uuid.uuid4().hex, *adapter_tested, out_client_id]])
        out_id = axon_device['adapters'][0]['data']['id']

        self.axonius_system.insert_device(axon_device)

        devices_response = get_devices_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name}

        assert gui_service.delete_client(self.adapter_service.unique_name, our_client_object_id).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        out_client_id = self.some_client_id

        devices_response = get_devices_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name}

        assert gui_service.delete_client(self.adapter_service.unique_name, our_client_object_id,
                                         params={
                                             'deleteEntities': 'True'
                                         }).status_code == 200
        assert len(get_devices_by_id(self.adapter_service.plugin_name, out_id)) == 0
        self.adapter_service.trigger_clean_db()

    def test_removing_adapter_creds_with_users(self):
        """
        This tests the feature that allows the user to delete a set of credentials from an adapter
        and also deleting all associated users to those credentials.
        """
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        out_client_id = self.some_client_id

        gui_service = self.axonius_system.gui
        gui_service.login_user(DEFAULT_USER)

        adapter_tested = [self.adapter_service.plugin_name,
                          self.adapter_service.unique_name]  # plugin_name, plugin_unique_name
        not_our_adapter = ['lol_adapter', 'lol_adapter_321']

        axon_device = get_entity_axonius_dict_multiadapter('GUI_CLIENT_DELETE_TEST',
                                                           [[uuid.uuid4().hex, *adapter_tested, out_client_id],
                                                            [uuid.uuid4().hex, *not_our_adapter]])
        out_id = axon_device['adapters'][0]['data']['id']
        lol_id = axon_device['adapters'][1]['data']['id']
        self.axonius_system.insert_user(axon_device)

        def get_users_by_id(adapter_name, data_id):
            res = gui_service.get_users(params={
                'filter':
                    f'adapters_data.{adapter_name}.id == \'{data_id}\''}).json()
            return res

        devices_response = get_users_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name, 'lol_adapter'}

        assert gui_service.delete_client(self.adapter_service.unique_name, our_client_object_id).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        out_client_id = self.some_client_id

        devices_response = get_users_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name, 'lol_adapter'}

        devices_response = get_users_by_id('lol_adapter', lol_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name, 'lol_adapter'}

        assert gui_service.delete_client(self.adapter_service.unique_name, our_client_object_id,
                                         params={
                                             'deleteEntities': 'True'
                                         }).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        out_client_id = self.some_client_id

        devices_response = get_users_by_id('lol_adapter', lol_id)[0]
        assert set(devices_response['adapters']) == {'lol_adapter'}
        assert len(get_users_by_id(self.adapter_service.plugin_name, out_id)) == 0

        # test without linked devices
        axon_device = get_entity_axonius_dict_multiadapter('GUI_CLIENT_DELETE_TEST',
                                                           [[uuid.uuid4().hex, *adapter_tested, out_client_id]])
        out_id = axon_device['adapters'][0]['data']['id']

        self.axonius_system.insert_user(axon_device)

        devices_response = get_users_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name}

        assert gui_service.delete_client(self.adapter_service.unique_name, our_client_object_id).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        out_client_id = self.some_client_id

        devices_response = get_users_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name}

        assert gui_service.delete_client(self.adapter_service.unique_name, our_client_object_id,
                                         params={
                                             'deleteEntities': 'True'
                                         }).status_code == 200
        assert len(get_users_by_id(self.adapter_service.plugin_name, out_id)) == 0
        self.adapter_service.trigger_clean_db()
