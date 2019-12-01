import base64
import os
import datetime
from collections import defaultdict
import traceback
from multiprocessing.pool import ThreadPool
from threading import Lock

import requests
from pymongo.collection import Collection

from axonius.consts.system_consts import WEAVE_NETWORK, DB_KEY_PATH
from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS_COLLECTION, GUI_PLUGIN_NAME, \
    AXONIUS_SETTINGS_DIR_NAME, GUI_SYSTEM_CONFIG_COLLECTION, NODE_ID, PLUGIN_NAME,\
    PLUGIN_UNIQUE_NAME, CORE_UNIQUE_NAME
from axonius.consts.adapter_consts import ADAPTER_PLUGIN_TYPE
from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.entities import EntityType
from axonius.utils.hash import get_preferred_quick_adapter_id
from axonius.utils import datetime
from axonius.utils.encryption.mongo_encrypt import MONGO_MASTER_KEY_SIZE
from services.plugin_service import PluginService, API_KEY_HEADER, UNIQUE_KEY_PARAM
from services.updatable_service import UpdatablePluginMixin


class CoreService(PluginService, UpdatablePluginMixin):
    def __init__(self):
        super().__init__('core')

    def _migrate_db(self):
        super()._migrate_db()
        if self.db_schema_version < 1:
            self._update_schema_version_1()

        if self.db_schema_version < 2:
            self._update_schema_version_2()

        if self.db_schema_version < 3:
            self._update_schema_version_3()

        if self.db_schema_version < 4:
            self._update_schema_version_4()

        if self.db_schema_version < 5:
            self._update_schema_version_5()

        if self.db_schema_version < 6:
            self._update_schema_version_6()

        if self.db_schema_version < 7:
            self._update_schema_version_7()

        if self.db_schema_version < 8:
            self._update_schema_version_8()

        if self.db_schema_version != 8:
            print(f'Upgrade failed, db_schema_version is {self.db_schema_version}')

    def _update_schema_version_1(self):
        print('Upgrade to schema 1')
        try:
            config_match = {
                'config_name': CORE_CONFIG_NAME
            }
            config_collection = self.db.get_collection(self.plugin_name, CONFIGURABLE_CONFIGS_COLLECTION)
            current_config = config_collection.find_one(config_match)
            if current_config:
                maintenance_config = current_config['config'].get('maintenance_settings')
                if maintenance_config:
                    self.db.get_collection(GUI_PLUGIN_NAME, GUI_SYSTEM_CONFIG_COLLECTION).insert_one({
                        'type': 'maintenance',
                        'provision': maintenance_config.get('analytics', True),
                        'analytics': maintenance_config.get('analytics', True),
                        'troubleshooting': maintenance_config.get('troubleshooting', True),
                        'timeout': None
                    })
                del current_config['config']['maintenance_settings']
                config_collection.replace_one(config_match, current_config)
            self.db_schema_version = 1
        except Exception as e:
            print(f'Exception while upgrading core db to version 1. Details: {e}')
            traceback.print_exc()

    def _update_schema_version_2(self):
        print('Upgrade to schema 2')
        try:
            registered_plugins = list(self.db.client['core']['configs'].find({'plugin_type': ADAPTER_PLUGIN_TYPE}))

            # Due to old bugs, we sometimes have multiple versions of the same adapter, running on the same node.
            # However, an adapter should be a singleton on a specific node. This is why we deprecate old instances
            # here.

            plugins_mapping = defaultdict(lambda: defaultdict(list))
            for x in registered_plugins:
                if NODE_ID not in x:
                    # This is a plugin that was not seen for an extremely large time
                    print(f'Deprecating {x[PLUGIN_UNIQUE_NAME]}')
                    self.db.deprecate_a_leftover_db(x[PLUGIN_UNIQUE_NAME])
                    continue
                plugins_mapping[x[NODE_ID]][x[PLUGIN_NAME]].append(x)

            for node_id, node_plugins in plugins_mapping.items():
                for plugin_name, all_plugin_name_instances_per_node in node_plugins.items():
                    if len(all_plugin_name_instances_per_node) == 1:
                        continue

                    last_seen = max(
                        all_plugin_name_instances_per_node,
                        key=lambda adapter_candidate:
                        adapter_candidate.get('last_seen') or datetime.datetime(year=2017, month=1, day=1)
                    )
                    leftover_adapters = [
                        x[PLUGIN_UNIQUE_NAME]
                        for x
                        in all_plugin_name_instances_per_node
                        if x[PLUGIN_UNIQUE_NAME] != last_seen[PLUGIN_UNIQUE_NAME]
                    ]

                    print(f'Node {node_id}: {last_seen[PLUGIN_UNIQUE_NAME]} is the newest, olds are all others: ' +
                          ', '.join(leftover_adapters))

                    for leftover in leftover_adapters:
                        print(f'Deprecating {leftover}')
                        self.db.deprecate_a_leftover_db(leftover)
            self.db_schema_version = 2
        except Exception as e:
            print(f'Exception while upgrading core db to version 2. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_3(self):
        # https://axonius.atlassian.net/browse/AX-4606
        print('Upgrade to schema 3')
        # This makes the strong assumption that this deployment of axonius has only a master and no nodes

        node_id = self.node_id
        if not node_id:
            print(f'Core is not registered, nothing to do here')
            self.db_schema_version = 3
            return

        try:
            plugins_collection: Collection = self.db.client[CORE_UNIQUE_NAME]['configs']
            actions_collection: Collection = self.db.client['reports']['saved_actions']

            update_res = actions_collection.update_many(filter={
                'action.config.instance': {
                    '$exists': True
                }
            }, update={
                '$set': {
                    'action.config.instance': node_id
                }
            })
            print(f'Updated {update_res.modified_count} saved actions, matched {update_res.matched_count}')

            update_res = plugins_collection.update_many(filter={
                PLUGIN_UNIQUE_NAME: {
                    '$ne': CORE_UNIQUE_NAME
                }
            }, update={
                '$set': {
                    NODE_ID: f'!{node_id}'
                }
            })

            print(f'Updated {update_res.modified_count} plugins, matched {update_res.matched_count}')
            self.db_schema_version = 3
        except Exception as e:
            print(f'Exception while upgrading core db to version 3. Details: {e}')
            traceback.print_exc()
            raise

    def perform_quick_register(self, doc: dict) -> requests.Response:
        """
        Performs a POST register call to Core
        :param doc: the doc to transfer
        """
        return requests.post(f'{self.req_url}/register', json=doc)

    def _update_schema_version_4(self):
        # https://axonius.atlassian.net/browse/AX-4732
        # https://axonius.atlassian.net/browse/AX-4733
        print('Upgrade to schema 4')
        try:
            stress_res = self.db.client['core']['configs'].delete_many({
                PLUGIN_NAME: 'stresstest_adapter'
            })
            stressuser_res = self.db.client['core']['configs'].delete_many({
                PLUGIN_NAME: 'stresstest_users_adapter'
            })
            print(f'Deleted {stress_res.deleted_count} stresstest and {stressuser_res.deleted_count} user stresstest')

            pm_status = self.db.client['core']['configs'].delete_many({
                PLUGIN_NAME: 'pm_status'
            })
            print(f'Deleted {pm_status.deleted_count} pm status')

            careful_exec = self.db.client['core']['configs'].delete_many({
                PLUGIN_NAME: 'careful_execution_correlator'
            })
            print(f'Deleted {careful_exec.deleted_count} careful exection')

            # Even if we delete too much, that's not really an issue, because it will just re-register
            old_stuff = self.db.client['core']['configs'].delete_many({
                'last_seen': {
                    '$lt': datetime.datetime.now() - datetime.timedelta(days=30)
                }
            })
            print(f'Deleted {old_stuff.deleted_count} old stuff')
            self.db_schema_version = 4
        except Exception as e:
            print(f'Exception while upgrading core db to version 4. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_5(self):
        # https://axonius.atlassian.net/browse/AX-5222
        # This fixes the hyperlinks by removing all existing hyperlinks data and allowing
        # the system to replace it with new data.
        # This is only needed once because of historical changes that caused issues with clients.
        print('Upgrade to schema 5')
        try:
            devices_field_col = self.db.client['aggregator']['devices_fields']
            users_field_col = self.db.client['aggregator']['users_fields']

            devices_res = devices_field_col.delete_many({
                'name': 'hyperlinks'
            })
            users_res = users_field_col.delete_many({
                'name': 'hyperlinks'
            })
            print(f'Deleted {devices_res.deleted_count} hyperlinks for devices and {users_res.deleted_count} '
                  f'hyperlinks for users')
            self.db_schema_version = 5
        except Exception as e:
            print(f'Exception while upgrading core db to version 5. Details: {e}')
            traceback.print_exc()
            raise

    def _fix_db_for_entity(self, entity_type: EntityType):
        col = self._entity_db_map[entity_type]
        estimated_count = col.estimated_document_count()
        start_time = datetime.datetime.now()
        print(f'Fixing for entity {entity_type}, count is {estimated_count}, starting at {start_time}')

        class Expando:
            pass

        o = Expando()

        o.counter = 0
        o.adapter_entities_counter = 0
        lock = Lock()
        cursor = col.find({
            'adapters': {
                '$elemMatch': {
                    'quick_id': {
                        '$exists': False
                    }
                }
            }
        }, projection={
            f'adapters.{PLUGIN_UNIQUE_NAME}': True,
            'adapters.data.id': True,
            '_id': True
        })

        def process_entity(entity):
            for adapter in entity['adapters']:
                col.update_one({
                    '_id': entity['_id'],
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: adapter[PLUGIN_UNIQUE_NAME],
                            'data.id': adapter['data']['id']
                        }
                    }
                }, {
                    '$set': {
                        'adapters.$.quick_id': get_preferred_quick_adapter_id(adapter[PLUGIN_UNIQUE_NAME],
                                                                              adapter['data']['id'])
                    }
                })
                with lock:
                    o.adapter_entities_counter += 1

            with lock:
                o.counter += 1
                if o.counter % 2000 == 0:
                    print(f'{o.counter} out of {estimated_count} completed, {(o.counter / estimated_count) * 100}%, '
                          f'took {(datetime.datetime.now() - start_time).total_seconds()} seconds')

        with ThreadPool(30) as pool:
            pool.map(process_entity, cursor)

        total_seconds = (datetime.datetime.now() - start_time).total_seconds()
        print(f'Took {total_seconds} seconds, {o.counter / total_seconds} entities/second, '
              f'total of {o.adapter_entities_counter} adapte entities, '
              f'{o.adapter_entities_counter / total_seconds} adapter entities/second')

    def _update_schema_version_6(self):
        # Adds 'quick_id' to all entities in users/devices db
        print('Upgrade to schema 6')
        try:
            self._fix_db_for_entity(EntityType.Devices)
            self._fix_db_for_entity(EntityType.Users)
            self.db_schema_version = 6
        except Exception as e:
            print(f'Exception while upgrading core db to version 6. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_7(self):
        # https://axonius.atlassian.net/browse/AX-5394
        # DB is corrupted for some customers (and demo-latest)
        print('Upgrade to schema 7')
        try:
            config_match = {
                'config_name': CORE_CONFIG_NAME
            }
            config_collection = self.db.get_collection(self.plugin_name, CONFIGURABLE_CONFIGS_COLLECTION)
            current_config = config_collection.find_one(config_match)
            if current_config:
                ssl_trust_setting = current_config['config'].get('ssl_trust_settings')
                if ssl_trust_setting and not isinstance(ssl_trust_setting.get('ca_files'), list):
                    ssl_trust_setting['ca_files'] = []
                    config_collection.replace_one(config_match, current_config)
            self.db_schema_version = 7
        except Exception as e:
            print(f'Exception while upgrading core db to version 7. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_8(self):
        # https://axonius.atlassian.net/browse/AX-5109
        print('Upgrade to schema 8')
        try:
            print('Creating DB encryption key')
            self.create_db_encryption_key()
            # Encrypt plugins creds
            plugins = self.db.client['core']['configs'].find(
                {
                    'plugin_type': 'Adapter'
                })
            for plugin in plugins:
                plugin_unique_name = plugin.get('plugin_unique_name')
                clients = self.db.client[plugin_unique_name]['clients'].find({})
                for client in clients:
                    client_config = client['client_config']
                    for key, val in client_config.items():
                        if client_config[key]:
                            client_config[key] = self.db_encrypt(plugin_unique_name, client_config[key])
                    self.db.client[plugin_unique_name]['clients'].update(
                        {
                            '_id': client['_id']
                        },
                        {
                            '$set':
                                {
                                    'client_config': client_config
                                }
                        })
            self.db_schema_version = 8
        except OSError as e:
            print('Cannot upgrade db to version 8, libmongocrypt error')
        except Exception as e:
            print(f'Exception while upgrading core db to version 8. Details: {e}')
            traceback.print_exc()
            raise

    def register(self, api_key=None, plugin_name=''):
        headers = {}
        params = {}
        if api_key:
            headers[API_KEY_HEADER] = api_key
            params[UNIQUE_KEY_PARAM] = plugin_name

        return requests.get(f'{self.req_url}/register', headers=headers, params=params)

    @property
    def volumes_override(self):
        # Creating a settings dir outside of cortex (on production machines
        # this will be /home/ubuntu/.axonius_settings) for login marker and weave encryption key.
        settings_path = os.path.abspath(os.path.join(self.cortex_root_dir, AXONIUS_SETTINGS_DIR_NAME))
        os.makedirs(settings_path, exist_ok=True)
        container_settings_dir_path = os.path.join('/home/axonius/', AXONIUS_SETTINGS_DIR_NAME)

        if self.docker_network == WEAVE_NETWORK:
            docker_socket_mapping = '/var/run/weave/weave.sock:/var/run/docker.sock'
        else:
            # running on a windows machine
            docker_socket_mapping = '/var/run/docker.sock:/var/run/docker.sock'
        volumes = [f'{settings_path}:{container_settings_dir_path}', docker_socket_mapping]

        volumes.extend(super().volumes_override)
        return volumes

    def _is_service_alive(self):
        try:
            r = self.version()
            return r.status_code == 200
        except Exception:
            return False

    def get_registered_plugins(self):
        return self.register()

    def set_config(self, config):
        self.db.get_collection('core', CONFIGURABLE_CONFIGS_COLLECTION).update_one(
            {'config_name': CORE_CONFIG_NAME},
            {'$set': config}
        )
        self.post('update_config')

    @property
    def get_max_uwsgi_threads(self) -> int:
        return 500

    @staticmethod
    def create_db_encryption_key():
        """
        Create mongo encryption master key file if it not exists
        :return: None
        """
        if not DB_KEY_PATH.is_file():
            try:
                with open(DB_KEY_PATH, 'wb') as f:
                    key = os.urandom(MONGO_MASTER_KEY_SIZE)
                    f.write(base64.b64encode(key))
                DB_KEY_PATH.chmod(0o646)
            except Exception as e:
                print(f'Error writing db encryption key: {e}')
                if DB_KEY_PATH.is_file():
                    DB_KEY_PATH.unlink()
