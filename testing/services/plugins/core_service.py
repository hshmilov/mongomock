import os
from collections import defaultdict
import traceback
from pathlib import Path

import requests
from pymongo.collection import Collection

from axonius.consts.system_consts import WEAVE_NETWORK
from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS_COLLECTION, GUI_PLUGIN_NAME, \
    AXONIUS_SETTINGS_DIR_NAME, GUI_SYSTEM_CONFIG_COLLECTION, NODE_ID, PLUGIN_NAME,\
    PLUGIN_UNIQUE_NAME, CORE_UNIQUE_NAME, NODE_ID_FILENAME
from axonius.consts.adapter_consts import ADAPTER_PLUGIN_TYPE
from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.utils import datetime
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

        if self.db_schema_version != 3:
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

        try:
            node_id_file_path = os.path.abspath(os.path.join(self.cortex_root_dir,
                                                             AXONIUS_SETTINGS_DIR_NAME,
                                                             NODE_ID_FILENAME))
            print(f'Reading node_id from {node_id_file_path}')
            node_id: str = Path(node_id_file_path).read_text().strip()
            del node_id_file_path
        except Exception as e:
            print(f'Core is not registered, nothing to do here, {e}')
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
