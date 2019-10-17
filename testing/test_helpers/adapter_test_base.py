import uuid
from datetime import datetime, timedelta, timezone

import pytest
from flaky import flaky

from axonius.consts.metric_consts import Adapters
from axonius.utils.hash import get_preferred_quick_adapter_id
from axonius.utils.wait import wait_until
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
    def adapter_has_constant_url(self):
        # By default, we assume that the user provides the url for the administration panel.
        # If that is not the case, like in AWS or GCP, then there is no point in testing 'Fake Client'.
        return False

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

    @property
    def log_tester(self):
        return self.adapter_service.log_tester

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

    def test_unique_dns(self):
        assert self.adapter_service.is_unique_dns_registered()

    @flaky(max_runs=2)
    def test_check_reachability(self):
        assert self.adapter_service.is_client_reachable(self.some_client_details)
        if not self.adapter_has_constant_url:
            assert not self.adapter_service.is_client_reachable(FAKE_CLIENT_DETAILS)

    @flaky(max_runs=2)
    def test_fetch_devices(self):
        self.adapter_service.add_client(self.some_client_details)
        wait_until(lambda: self.log_tester.is_metric_in_log(metric_name=Adapters.CREDENTIALS_CHANGE_OK,
                                                            value='.*',
                                                            lines_lookback=10))

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
        id2_ = '2-' + uuid.uuid4().hex
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
                    'quick_id': get_preferred_quick_adapter_id(self.adapter_service.unique_name, id2_),
                    'data': {
                        'id': id2_,
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
            id4_ = '4-' + uuid.uuid4().hex
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
                        'quick_id': get_preferred_quick_adapter_id(self.adapter_service.unique_name, id4_),
                        'data': {
                            'id': id4_,
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
                        'quick_id': get_preferred_quick_adapter_id(self.adapter_service.unique_name,
                                                                   deleted_adapter_entity_id),
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
                        'quick_id': get_preferred_quick_adapter_id('high_capacity_carburetor_adapter_1337',
                                                                   not_deleted_adapter_entity_id),
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
            id9_ = '9-' + uuid.uuid4().hex
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
                        'quick_id': get_preferred_quick_adapter_id(self.adapter_service.unique_name,
                                                                   id9_),
                        'data': {
                            'id': id9_,
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

    @pytest.mark.skip('Useless and takes a lot of time')
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

        assert gui_service.delete_client(self.adapter_service.plugin_name, our_client_object_id).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']

        devices_response = get_devices_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name, 'lol_adapter'}

        devices_response = get_devices_by_id('lol_adapter', lol_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name, 'lol_adapter'}

        assert gui_service.delete_client(self.adapter_service.plugin_name, our_client_object_id,
                                         params={
                                             'deleteEntities': 'True'
                                         }).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        out_client_id = self.some_client_id

        devices_response = get_devices_by_id('lol_adapter', lol_id)[0]
        assert set(devices_response['adapters']) == {'lol_adapter'}
        devices_response = get_devices_by_id(self.adapter_service.plugin_name, out_id)
        assert len(devices_response) == 0

        # test without linked devices
        axon_device = get_entity_axonius_dict_multiadapter('GUI_CLIENT_DELETE_TEST',
                                                           [[uuid.uuid4().hex, *adapter_tested, out_client_id]])
        out_id = axon_device['adapters'][0]['data']['id']

        self.axonius_system.insert_device(axon_device)

        devices_response = get_devices_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name}

        assert gui_service.delete_client(self.adapter_service.plugin_name, our_client_object_id).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']

        devices_response = get_devices_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name}

        assert gui_service.delete_client(self.adapter_service.plugin_name, our_client_object_id,
                                         params={
                                             'deleteEntities': 'True'
                                         }).status_code == 200
        res = get_devices_by_id(self.adapter_service.plugin_name, out_id)
        assert len(res) == 0
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

        assert gui_service.delete_client(self.adapter_service.plugin_name, our_client_object_id).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        out_client_id = self.some_client_id

        devices_response = get_users_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name, 'lol_adapter'}

        devices_response = get_users_by_id('lol_adapter', lol_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name, 'lol_adapter'}

        assert gui_service.delete_client(self.adapter_service.plugin_name, our_client_object_id,
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

        assert gui_service.delete_client(self.adapter_service.plugin_name, our_client_object_id).status_code == 200
        our_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']

        devices_response = get_users_by_id(self.adapter_service.plugin_name, out_id)[0]
        assert set(devices_response['adapters']) == {self.adapter_service.plugin_name}

        assert gui_service.delete_client(self.adapter_service.plugin_name, our_client_object_id,
                                         params={'deleteEntities': 'True'}).status_code == 200
        assert len(get_users_by_id(self.adapter_service.plugin_name, out_id)) == 0
        self.adapter_service.trigger_clean_db()

    def test_bad_client(self):
        try:
            self.adapter_service.add_client(FAKE_CLIENT_DETAILS)
        except AssertionError:
            pass  # some adapters return 200, and some an error
        wait_until(lambda: self.log_tester.is_metric_in_log(metric_name=Adapters.CREDENTIALS_CHANGE_ERROR,
                                                            value='.*'))
