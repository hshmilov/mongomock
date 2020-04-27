import logging
from collections import defaultdict
import json
import gridfs
import pymongo
from flask import (jsonify,
                   request)

from axonius.consts import adapter_consts
from axonius.consts.core_consts import ACTIVATED_NODE_STATUS, DEACTIVATED_NODE_STATUS
from axonius.consts.plugin_consts import (CORE_UNIQUE_NAME,
                                          NODE_ID, NODE_NAME, PLUGIN_NAME, PLUGIN_UNIQUE_NAME,
                                          STATIC_CORRELATOR_PLUGIN_NAME,
                                          STATIC_USERS_CORRELATOR_PLUGIN_NAME,
                                          CONFIGURABLE_CONFIGS_COLLECTION)
from axonius.plugin_base import return_error
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

    @staticmethod
    def _get_plugin_schemas(db_connection, plugin_unique_name):
        """
        Get all schemas for a given plugin
        :param db: a db connection
        :param plugin_unique_name: the unique name of the plugin
        :return: dict
        """

        clients_value = db_connection[plugin_unique_name]['adapter_schema'].find_one(sort=[('adapter_version',
                                                                                            pymongo.DESCENDING)])
        if clients_value is None:
            return {}
        return {'clients': clients_value.get('schema')}

    @gui_route_logged_in()
    def adapters(self):
        return jsonify(self._adapters())

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

            schema = self._get_plugin_schemas(db_connection, adapter_name).get('clients')
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
                'config': self.__extract_configs_and_schemas(db_connection,
                                                             adapter_name)
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
                logger.exception(f'Failed fetching from {adapter_unique_name} for {client_to_add}', exc_info=err)

            self._async_trigger_remote_plugin(adapter_unique_name,
                                              'insert_to_db',
                                              data={
                                                  'client_name': client_id
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
        db_connection = self._get_db_connection()
        fs = gridfs.GridFS(db_connection[plugin_unique_name])
        written_file = fs.put(file, filename=filename)
        return jsonify({'uuid': str(written_file)})

    @staticmethod
    def __extract_configs_and_schemas(db_connection, plugin_unique_name):
        """
        Gets the configs and configs schemas in a nice way for a specific plugin
        """
        plugin_data = {}
        schemas = list(db_connection[plugin_unique_name]['config_schemas'].find())
        configs = list(db_connection[plugin_unique_name][CONFIGURABLE_CONFIGS_COLLECTION].find())
        for schema in schemas:
            associated_config = [c for c in configs if c['config_name'] == schema['config_name']]
            if not associated_config:
                logger.error(f'Found schema without associated config for {plugin_unique_name}' +
                             f' - {schema["config_name"]}')
                continue
            associated_config = associated_config[0]
            plugin_data[associated_config['config_name']] = {
                'schema': schema['schema'],
                'config': associated_config['config']
            }
        return plugin_data

    @gui_route_logged_in('<adapter_name>/<config_name>', methods=['POST'], enforce_trial=False,
                         activity_params=['adapter_name', 'config_name'])
    def update_adapter(self, adapter_name, config_name):
        response = self._save_plugin_config(adapter_name, config_name)
        if response != '':
            return response
        unique_names = self.request_remote_plugin(f'find_plugin_unique_name/nodes/None/plugins/{adapter_name}').json()
        if not unique_names:
            return response
        config_schema = self._get_collection('config_schemas', unique_names[0]).find_one({
            'config_name': config_name
        }, {
            'schema.pretty_name': 1
        })
        return json.dumps({
            'config_name': config_schema['schema'].get('pretty_name', '')
        }) if config_schema else ''
