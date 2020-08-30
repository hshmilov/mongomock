import logging
import re
from collections import defaultdict
import json
import pymongo
from flask import (jsonify,
                   request)

from axonius.consts import adapter_consts
from axonius.consts.adapter_consts import CLIENT_ID, CONNECTION_LABEL
from axonius.consts.core_consts import ACTIVATED_NODE_STATUS, DEACTIVATED_NODE_STATUS
from axonius.consts.gui_consts import FeatureFlagsNames
from axonius.consts.plugin_consts import (CORE_UNIQUE_NAME,
                                          NODE_ID, NODE_NAME, PLUGIN_NAME, PLUGIN_UNIQUE_NAME,
                                          STATIC_CORRELATOR_PLUGIN_NAME,
                                          STATIC_USERS_CORRELATOR_PLUGIN_NAME, CONNECT_VIA_TUNNEL,
                                          DISCOVERY_CONFIG_NAME, CONNECTION_DISCOVERY_SCHEMA_NAME)
from axonius.plugin_base import return_error
from axonius.utils.gui_helpers import return_api_format
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue

from axonius.utils.revving_cache import rev_cached
from axonius.utils.threading import run_and_forget
from gui.logic.db_helpers import beautify_db_entry
from gui.logic.login_helper import clear_passwords_fields
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.routes.adapters.connections import Connections

# pylint: disable=no-member,cell-var-from-loop

logger = logging.getLogger(f'axonius.{__name__}')


@gui_category_add_rules('adapters')
class Adapters(Connections):

    def _get_plugin_schemas(self, plugin_name):
        """
        Get all schemas for a given plugin
        :param plugin_name: the unique name of the plugin
        :return: dict
        """

        clients_value = self.plugins.get_plugin_settings(plugin_name).adapter_client_schema

        if clients_value is None:
            return {}
        return {'schema': clients_value}

    @return_api_format()
    @gui_route_logged_in(enforce_trial=False)
    def adapters(self, api_format=True):
        if api_format:
            adapters = self._adapters()
            for adapter_name in adapters.keys():
                for adapter in adapters[adapter_name]:
                    for client in adapter['clients']:
                        client_label = self.adapter_client_labels_db.find_one({
                            'client_id': client['client_id'],
                            PLUGIN_NAME: adapter_name,
                            NODE_ID: adapter[NODE_ID]
                        }, {
                            CONNECTION_LABEL: 1
                        })
                        client['client_config'][CONNECTION_LABEL] = (client_label.get(CONNECTION_LABEL, '')
                                                                     if client_label else '')
            return jsonify(adapters)
        return jsonify(self._adapters_v2())

    @gui_route_logged_in('hint_raise/<plugin_name>', methods=['POST'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.Adapters), skip_activity=True)
    def hint_raise_adapter(self, plugin_name: str):
        """
        Raises all instances of the given plugin name
        """
        plugins_to_raise = self.core_configs_collection.find({
            PLUGIN_NAME: plugin_name,
            'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE,
            'status': {
                '$ne': 'up'
            }
        }, projection={
            PLUGIN_UNIQUE_NAME: True
        })
        for plugin in plugins_to_raise:
            unique_name = plugin[PLUGIN_UNIQUE_NAME]
            # 'lives_left' is a variable that accounts for the amount of minutes of grace
            # for the adapter until it shuts down again
            self._get_collection('lives_left', db_name=unique_name).update_one(
                {
                    'lives_left': {
                        '$exists': True
                    }
                },
                {
                    '$set': {
                        'lives_left': 5
                    }
                }, upsert=True)
            run_and_forget(lambda: self.request_remote_plugin('version', plugin_unique_name=unique_name))
        return ''

    @gui_route_logged_in('<plugin_name>/advanced_settings', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.Adapters))
    def get_adapter_advanced_settings_schema(self, plugin_name):
        return jsonify(self._adapter_advanced_config_schema(plugin_name))

    @rev_cached(ttl=10, remove_from_cache_ttl=60)
    def _adapters_v2(self):
        """
        Get lean structure of adapters
        :return:
        """
        db_connection = self._get_db_connection()
        core_db = db_connection[CORE_UNIQUE_NAME]

        instances_metadata_db = core_db['nodes_metadata']

        # get all registered adapters from core
        registered_adapters = core_db['configs'].find({
            'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE,
            'hidden': {
                '$ne': True
            }
        }).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])

        adapters_result = defaultdict(list)

        for adapter in registered_adapters:

            # adapter_unique_name is the name in which this instance registered to core
            adapter_unique_name = adapter[PLUGIN_UNIQUE_NAME]
            adapter_name = adapter['plugin_name']

            current_adapter_db = db_connection[adapter_unique_name]

            adapter_instance_id = adapter[NODE_ID]
            instance_metadata = instances_metadata_db.find_one({
                NODE_ID: adapter_instance_id
            })

            # skip deactivated nodes.
            if instance_metadata and instance_metadata.get('status', ACTIVATED_NODE_STATUS) == DEACTIVATED_NODE_STATUS:
                continue

            node_name = '' if instance_metadata is None else instance_metadata.get(NODE_NAME)

            # get all adapter instance clients
            adapter_clients_success = current_adapter_db['clients'].count_documents({'status': 'success'})
            adapter_clients_count = current_adapter_db['clients'].count_documents({})

            # add the adapter into the response dict
            adapters_result[adapter_name].append({
                'plugin_name': adapter['plugin_name'],
                'unique_plugin_name': adapter_unique_name,
                'status': adapter.get('status', ''),
                'supported_features': adapter['supported_features'],
                'clients_count': adapter_clients_count,
                'success_clients': adapter_clients_success,
                NODE_NAME: node_name,
                NODE_ID: adapter[NODE_ID]
            })

        return adapters_result

    @rev_cached(ttl=10, remove_from_cache_ttl=60)
    def _adapter_advanced_config_schema(self, adapter_unique_name):
        db_connection = self._get_db_connection()
        return self.__extract_configs_and_schemas(adapter_unique_name)

    @rev_cached(ttl=10, remove_from_cache_ttl=60)
    def _get_adapter_connections_data(self, plugin_name):
        db_connection = self._get_db_connection()
        core_db = db_connection[CORE_UNIQUE_NAME]
        instances_metadata_db = core_db['nodes_metadata']

        registered_adapter_instances = core_db['configs'].find({
            'plugin_name': plugin_name,
            'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE,
            'hidden': {
                '$ne': True
            }
        }).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])

        # in a saas machines, the adapter page need one setting from the adapters settings to notify
        # the user about his state. this code will run only in sass machine and will get that setting
        # and send it to the GUi
        settings = {}
        if self.feature_flags_config().get(FeatureFlagsNames.EnableSaaS, False):
            adapter_settings = self.plugins.get_plugin_settings(plugin_name).configurable_configs.adapter_configuration
            if CONNECT_VIA_TUNNEL in adapter_settings:
                settings[CONNECT_VIA_TUNNEL] = adapter_settings[CONNECT_VIA_TUNNEL]

        clients_result = []
        schema = None
        client_connection_discovery_schema = {}
        for adapter in registered_adapter_instances:

            # adapter_unique_name is the name in which this instance registered to core
            adapter_unique_name = adapter[PLUGIN_UNIQUE_NAME]
            adapter_instance_db = db_connection[adapter_unique_name]

            adapter_instance_id = adapter[NODE_ID]
            instance_metadata = instances_metadata_db.find_one({
                NODE_ID: adapter_instance_id
            })

            # skip deactivated nodes.
            if instance_metadata and instance_metadata.get('status', ACTIVATED_NODE_STATUS) == DEACTIVATED_NODE_STATUS:
                continue

            client_configuration_schema = self._get_plugin_schemas(adapter[PLUGIN_NAME]).get('schema')
            client_connection_discovery_schema = self.plugins.get_plugin_settings(
                adapter[PLUGIN_NAME]).generic_schemas[CONNECTION_DISCOVERY_SCHEMA_NAME]

            # skip clients not properly configured or missing schema.
            if not client_configuration_schema:
                continue

            if not schema:
                # we take the first schema found, as it is the same for all instances of the same adapter.
                schema = client_configuration_schema

            node_name = '' if instance_metadata is None else instance_metadata.get(NODE_NAME)

            for client_data in adapter_instance_db['clients'].find({}):
                client = beautify_db_entry(client_data)

                self._decrypt_client_config(client['client_config'])
                client['client_config'] = clear_passwords_fields(client['client_config'], client_configuration_schema)
                client[NODE_ID] = adapter_instance_id
                client[NODE_NAME] = node_name
                client['adapter_name'] = adapter[PLUGIN_NAME]

                clients_result.append(client)

        return {
            'schema': schema,
            'clients': clients_result,
            'connectionDiscoverySchema': client_connection_discovery_schema,
            'settings': settings
        }

    @rev_cached(ttl=10, remove_from_cache_ttl=60)
    def _adapters(self):
        """
        Get all adapters from the core
        :return:
        """
        db_connection = self._get_db_connection()
        adapters_from_db = db_connection[CORE_UNIQUE_NAME]['configs'].find({
            'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE,
            'hidden': {
                '$ne': True
            }
        }).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
        adapters_to_return = []
        for adapter in adapters_from_db:
            adapter_name = adapter[PLUGIN_UNIQUE_NAME]

            schema = self._get_plugin_schemas(adapter[PLUGIN_NAME]).get('schema')
            nodes_metadata_collection = db_connection['core']['nodes_metadata']

            node_name = nodes_metadata_collection.find_one({
                NODE_ID: adapter[NODE_ID]
            })

            # Skip Deactivated nodes.
            if node_name and node_name.get('status', ACTIVATED_NODE_STATUS) == DEACTIVATED_NODE_STATUS:
                continue

            if not schema:
                # there might be a race - in the split second that the adapter is up
                # but it still hasn't written it's schema
                continue

            clients = [beautify_db_entry(client)
                       for client
                       in db_connection[adapter_name]['clients'].find().sort([('_id', pymongo.DESCENDING)])]
            for client in clients:
                self._decrypt_client_config(client['client_config'])
                client['client_config'] = clear_passwords_fields(client['client_config'], schema)
                client[NODE_ID] = adapter[NODE_ID]
                client['adapter_name'] = adapter[PLUGIN_NAME]
            status = ''
            if len(clients):
                status = 'success' if all(client.get('status') == 'success' for client in clients) \
                    else 'warning'

            node_name = '' if node_name is None else node_name.get(NODE_NAME)

            adapters_to_return.append({
                'plugin_name': adapter['plugin_name'],
                'unique_plugin_name': adapter_name,
                'status': status,
                'supported_features': adapter['supported_features'],
                'schema': schema,
                'clients': clients,
                NODE_ID: adapter[NODE_ID],
                NODE_NAME: node_name,
                'config': self.__extract_configs_and_schemas(adapter_name)
            })

        adapters = defaultdict(list)
        for adapter in adapters_to_return:
            plugin_name = adapter.pop('plugin_name')
            adapters[plugin_name].append(adapter)

        return adapters

    @gui_route_logged_in('adapter_features')
    def adapter_features(self):
        """
        Getting the features of each registered adapter, as they are saved in core's "configs" db.
        This is needed for the case that user has permissions to disable entities but is restricted from adapters.
        The user would need to know which entities can be disabled, according to the features of their adapters.

        :return: Dict between unique plugin name of the adapter and their list of features
        """
        plugins_available = self.get_available_plugins_from_core()
        db_connection = self._get_db_connection()
        adapters_from_db = db_connection['core']['configs'].find({
            'plugin_type': {
                '$in': [
                    'Adapter', 'ScannerAdapter'
                ]
            }
        }).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
        adapters_by_unique_name = {}
        for adapter in adapters_from_db:
            adapter_name = adapter[PLUGIN_UNIQUE_NAME]
            if adapter_name not in plugins_available:
                # Plugin not registered - unwanted in UI
                continue
            adapters_by_unique_name[adapter_name] = adapter['supported_features']
        return jsonify(adapters_by_unique_name)

    def _fetch_after_clients_thread(self, adapter_unique_name, client_id, client_to_add):
        # if there's no aggregator, that's fine
        try:
            logger.info(f'Requesting {adapter_unique_name} to fetch data from newly added client {client_id}')

            def inserted_to_db(*_):
                logger.info(f'{adapter_unique_name} finished fetching data for {client_id}')
                self._trigger('clear_dashboard_cache', blocking=False)
                self._trigger_remote_plugin(STATIC_CORRELATOR_PLUGIN_NAME)
                self._trigger_remote_plugin(STATIC_USERS_CORRELATOR_PLUGIN_NAME)
                self._trigger('clear_dashboard_cache', blocking=False)

            def rejected(err):
                logger.exception(f'Failed fetching from {adapter_unique_name}', exc_info=err)

            self._async_trigger_remote_plugin(adapter_unique_name,
                                              'insert_to_db',
                                              data={
                                                  'client_name': client_id,
                                                  'connection_saved': True,
                                              }).then(did_fulfill=inserted_to_db,
                                                      did_reject=rejected)

        except Exception:
            # if there's no aggregator, there's nothing we can do
            logger.exception(f'Error fetching devices from {adapter_unique_name} for client {client_to_add}')

    @gui_route_logged_in('<adapter_name>/<node_id>/upload_file', methods=['POST'],
                         required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Adapters),
                         skip_activity=True)
    def adapter_upload_file(self, adapter_name, node_id):
        adapter_unique_name = self.request_remote_plugin(
            f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}').json().get('plugin_unique_name')

        return self._upload_file(adapter_unique_name)

    def _upload_file(self, plugin_unique_name):
        field_name = request.form.get('field_name')
        if not field_name:
            return return_error('Field name must be specified', 401)
        file = request.files.get('userfile')
        if not file or file.filename == '':
            return return_error('File must exist', 401)
        filename = file.filename

        written_file = self.db_files.upload_file(file, filename=filename)
        return jsonify({'uuid': str(written_file)})

    def __extract_configs_and_schemas(self, plugin_unique_name):
        """
        Gets the configs and configs schemas in a nice way for a specific plugin
        """

        plugin_name = self._get_plugin_name(plugin_unique_name)

        plugin_data = {}
        schemas = self.plugins.get_plugin_settings(plugin_name).config_schemas.get_all()
        configs = self.plugins.get_plugin_settings(plugin_name).configurable_configs.get_all()

        for schema_config_name, schema in schemas.items():
            associated_config = [(name, config) for name, config in configs.items() if name == schema_config_name]
            if not associated_config:
                logger.error(f'Found schema without associated config for {plugin_unique_name}' +
                             f' - {schema_config_name}')
                continue
            associated_config = associated_config[0]

            associated_config_name, associated_config_config = associated_config
            plugin_data[associated_config_name] = {
                'schema': schema,
                'config': associated_config_config
            }
        return plugin_data

    def _get_adapter_connection_discovery_config_and_schema(self, plugin_unique_name):
        schema, config = self.plugins.get_plugin_config_and_schema(DISCOVERY_CONFIG_NAME, plugin_unique_name)
        config = clear_passwords_fields(config, schema)
        return config, schema

    @gui_route_logged_in('<adapter_name>/<config_name>', methods=['POST'], enforce_trial=False,
                         activity_params=['adapter_name', 'config_name'])
    def update_adapter(self, adapter_name, config_name):
        response = self._save_plugin_config(adapter_name, config_name)
        self._adapter_advanced_config_schema.clean_cache()
        if response != '':
            return response

        config_schema = self.plugins.get_plugin_settings(adapter_name).config_schemas[config_name]
        self._get_adapter_connections_data.clean_cache()
        return json.dumps({
            'config_name': config_schema.get('pretty_name', '')
        }) if config_schema else ''

    @gui_route_logged_in('<plugin_name>/<config_name>', methods=['GET'], enforce_trial=False)
    def get_plugin_configs(self, plugin_name, config_name):
        """
        Get a specific config on a specific plugin
        """
        plugin_name = self._get_plugin_name(plugin_name)
        config, schema = self._get_plugin_configs(config_name, plugin_name)

        return jsonify({
            'config': config,
            'schema': schema
        })

    @gui_route_logged_in('labels', methods=['GET'], enforce_permissions=False)
    def adapters_client_labels(self) -> list:
        """
        :return: list of connection label mapping -> [{client_id,connection_label,plugin_uniq_name,node_id}} ]  instance
        """
        clients_label = []
        labels_from_db = self.adapter_client_labels_db.find({})
        for client in labels_from_db:
            client_id = client.get(CLIENT_ID)
            connection_label = client.get(CONNECTION_LABEL)
            plugin_name = client.get(PLUGIN_NAME)
            plugin_unique_name = client.get(PLUGIN_UNIQUE_NAME)
            if client_id and connection_label and plugin_name and plugin_unique_name:
                clients_label.append({
                    'client_id': client_id,
                    'label': connection_label,
                    'plugin_name': plugin_name,
                    'plugin_unique_name': plugin_unique_name,
                    'node_id': client.get(NODE_ID)
                })
            else:
                logger.error(f'Invalid connection label, missing {client_id}, {connection_label}, {plugin_name}')

        return jsonify(clients_label)

    def _get_plugin_configs(self, config_name, plugin_name):
        plugin_name = self._get_plugin_name(plugin_name)
        schema = self.plugins.get_plugin_settings(plugin_name).config_schemas[config_name]
        config = clear_passwords_fields(
            self.plugins.get_plugin_settings(plugin_name).configurable_configs[config_name],
            schema
        )

        return config, schema

    @staticmethod
    def _get_plugin_name(plugin_unique_name):
        if re.search(r'_(\d+)$', plugin_unique_name):
            plugin_name = '_'.join(plugin_unique_name.split('_')[:-1])  # turn plugin unique name to plugin name
        else:
            plugin_name = plugin_unique_name

        return plugin_name
