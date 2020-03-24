import logging
import time
from collections import defaultdict
from multiprocessing.pool import ThreadPool

import gridfs
import pymongo
from bson import ObjectId
from flask import (jsonify,
                   request)

from axonius.consts import adapter_consts
from axonius.consts.adapter_consts import CLIENT_ID, CONNECTION_LABEL
from axonius.consts.core_consts import ACTIVATED_NODE_STATUS, DEACTIVATED_NODE_STATUS
from axonius.consts.plugin_consts import (CORE_UNIQUE_NAME,
                                          NODE_ID, NODE_NAME, PLUGIN_NAME, PLUGIN_UNIQUE_NAME,
                                          STATIC_CORRELATOR_PLUGIN_NAME,
                                          STATIC_USERS_CORRELATOR_PLUGIN_NAME,
                                          CONFIGURABLE_CONFIGS_COLLECTION)
from axonius.consts.gui_consts import (FeatureFlagsNames)
from axonius.plugin_base import EntityType, return_error
from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType, entity_fields)
from axonius.utils.revving_cache import rev_cached
from axonius.utils.threading import run_and_forget
from gui.logic.db_helpers import beautify_db_entry
from gui.logic.login_helper import clear_passwords_fields, \
    refill_passwords_fields, has_unchanged_password_value
from gui.logic.routing_helper import gui_add_rule_logged_in
# pylint: disable=no-member,cell-var-from-loop,access-member-before-definition,logging-not-lazy

logger = logging.getLogger(f'axonius.{__name__}')


class Adapters:
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

    @gui_add_rule_logged_in('adapters', required_permissions={Permission(PermissionType.Adapters,
                                                                         PermissionLevel.ReadOnly)})
    def adapters(self):
        return jsonify(self._adapters())

    @gui_add_rule_logged_in('adapters/hint_raise/<plugin_name>',
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadOnly)},
                            methods=['POST'])
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

    @gui_add_rule_logged_in('adapter_features')
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

    def _test_client_connectivity(self, adapter_unique_name, data_from_db_for_unchanged=None):
        client_to_test = request.get_json(silent=True)
        if client_to_test is None:
            return return_error('Invalid client', 400)
        if data_from_db_for_unchanged:
            client_to_test = refill_passwords_fields(client_to_test, data_from_db_for_unchanged['client_config'])
        # adding client to specific adapter
        response = self.request_remote_plugin('client_test', adapter_unique_name, method='post',
                                              json=client_to_test)
        if response.status_code != 200:
            logger.error(f'Error in client adding: {response.status_code}, {response.text}')
        return response.text, response.status_code

    def _query_client_for_devices(self, adapter_unique_name, clients):
        if clients is None:
            return return_error('Invalid client', 400)
        # adding client to specific adapter
        response = self.request_remote_plugin('clients', adapter_unique_name, 'put', json=clients,
                                              raise_on_network_error=True)
        self._adapters.clean_cache()
        self.clients_labels.clean_cache()

        if response.status_code == 200:
            self._client_insertion_threadpool.submit(self._fetch_after_clients_thread, adapter_unique_name,
                                                     response.json()['client_id'], clients)
        else:
            logger.error(f'Error in client adding: {response.status_code}, {response.text}')
        return response.text, response.status_code

    def validate_and_fill_unchanged_passwords_fields(self,
                                                     adapter_unique_name: str,
                                                     client_id: str,
                                                     data: object,
                                                     data_for_unchanged_passwords: dict) -> bool:
        """
        Check if there is an unchanged password with a changed client_id
        :param adapter_unique_name: the adapter name
        :param client_id: the old client_id (from the db)
        :param data: the data to change
        :param data_for_unchanged_passwords: the data from the db for filling the unchanged passwords
        :return: True if the data is valid False if not
        """
        if not has_unchanged_password_value(data):
            return True
        if data_for_unchanged_passwords:
            refill_passwords_fields(data, data_for_unchanged_passwords)
        get_client_id_response = self.request_remote_plugin('get_client_id', adapter_unique_name, 'post', json=data,
                                                            raise_on_network_error=True)
        if not get_client_id_response or not get_client_id_response.text:
            return False
        # return True if the new client id equals to client_id in the db
        return get_client_id_response.text == client_id

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

    @gui_add_rule_logged_in('adapters/<adapter_name>/<node_id>/upload_file', methods=['POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
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

    @gui_add_rule_logged_in('adapters/<adapter_name>/clients', methods=['PUT', 'POST'],
                            required_permissions={Permission(PermissionType.Adapters,
                                                             PermissionLevel.ReadWrite)})
    def adapters_clients(self, adapter_name):
        return self._adapters_clients(adapter_name)

    def _adapters_clients(self, adapter_name):
        """
        Gets or creates clients in the adapter
        :param adapter_name: the adapter to refer to
        :return:
        """
        clients = request.get_json(silent=True)
        node_id = clients.pop('instanceName', self.node_id)

        adapter_unique_name = self.request_remote_plugin(
            f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}').json().get('plugin_unique_name')
        logger.info(f'Got adapter unique name {adapter_unique_name}')
        if request.method == 'PUT':
            def reset_cache_soon():
                time.sleep(5)
                entity_fields.clean_cache()

            if self._is_system_first_use:
                run_and_forget(reset_cache_soon())

            self._is_system_first_use = False
            return self._query_client_for_devices(adapter_unique_name, clients)
        return self._test_client_connectivity(adapter_unique_name)

    @gui_add_rule_logged_in('adapters/<adapter_name>/clients/<client_id>',
                            methods=['PUT', 'DELETE'], required_permissions={Permission(PermissionType.Adapters,
                                                                                        PermissionLevel.ReadWrite)})
    def adapters_clients_update(self, adapter_name, client_id=None):
        return self._adapters_clients_update(adapter_name, client_id)

    def _adapters_clients_update(self, adapter_name, client_id=None):
        """
        Create or delete credential sets (clients) in the adapter
        :param adapter_name: the adapter to refer to
        :param client_id: UUID of client to delete if DELETE is used
        :return:
        """
        data = self.get_request_data_as_object()
        node_id = data.pop('instanceName', self.node_id)
        old_node_id = data.pop('oldInstanceName', None)
        try:
            adapter_unique_name = self.request_remote_plugin(f'find_plugin_unique_name/nodes/{old_node_id or node_id}/'
                                                             f'plugins/{adapter_name}').json().get(PLUGIN_UNIQUE_NAME)
        except Exception:
            raise ValueError(f'adapter {adapter_name} with instance_name {node_id} and old_instance_name {old_node_id}'
                             f' not found')
        if request.method == 'DELETE':
            if request.args.get('deleteEntities', False):
                self.delete_client_data(adapter_name, adapter_unique_name, client_id)

        client_from_db = self._get_collection('clients', adapter_unique_name).find_one({'_id': ObjectId(client_id)})
        if not client_from_db:
            return return_error('Server is already gone, please try again after refreshing the page')
        self._decrypt_client_config(client_from_db['client_config'])
        if request.method == 'PUT' and \
                not self.validate_and_fill_unchanged_passwords_fields(adapter_unique_name,
                                                                      client_from_db['client_id'],
                                                                      data,
                                                                      client_from_db['client_config']) \
                and self.feature_flags_config().get(FeatureFlagsNames.ReenterCredentials):
            return return_error('Failed to save connection details. '
                                'Changing connection details requires re-entering credentials', 400)
        self.request_remote_plugin('clients/' + client_id, adapter_unique_name, method='delete')
        if request.method == 'PUT':
            if old_node_id != node_id:
                url = f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}'
                adapter_unique_name = self.request_remote_plugin(url).json().get('plugin_unique_name')

            self._adapters.clean_cache()
            self.clients_labels.clean_cache()
            return self._query_client_for_devices(adapter_unique_name, data)

        self._adapters.clean_cache()
        self.clients_labels.clean_cache()

        return '', 200

    def delete_client_data(self, plugin_name, plugin_unique_name, client_id):
        client_from_db = self._get_collection('clients', plugin_unique_name).find_one({'_id': ObjectId(client_id)})
        if client_from_db:
            # this is the "client_id" - i.e. AD server or AWS Access Key
            logger.info(f'User deleted client - Deleting entities for {plugin_unique_name} - {client_id}')
            local_client_id = client_from_db['client_id']
            for entity_type in EntityType:
                res = self._entity_db_map[entity_type].update_many(
                    {
                        'adapters': {
                            '$elemMatch': {
                                '$and': [
                                    {
                                        PLUGIN_NAME: plugin_name
                                    },
                                    {
                                        # and the device must be from this adapter
                                        'client_used': local_client_id
                                    }
                                ]
                            }
                        }
                    },
                    {
                        '$set': {
                            'adapters.$[i].pending_delete': True
                        }
                    },
                    array_filters=[
                        {
                            '$and': [
                                {f'i.{PLUGIN_NAME}': plugin_name},
                                {'i.client_used': local_client_id}
                            ]
                        }
                    ]
                )

                logger.info(f'Set pending_delete on {res.modified_count} axonius entities '
                            f'(or some adapters in them) ' +
                            f'from {res.matched_count} matches')

                entities_to_pass_to_be_deleted = list(self._entity_db_map[entity_type].find(
                    {
                        'adapters': {
                            '$elemMatch': {
                                '$and': [
                                    {
                                        PLUGIN_NAME: plugin_name
                                    },
                                    {
                                        # and the device must be from this adapter
                                        'client_used': local_client_id
                                    }
                                ]
                            }
                        }
                    },
                    projection={
                        'adapters.client_used': True,
                        'adapters.data.id': True,
                        f'adapters.{PLUGIN_UNIQUE_NAME}': True,
                        f'adapters.{PLUGIN_NAME}': True,
                    }))

                def async_delete_entities(entity_type, entities_to_delete):
                    with ThreadPool(5) as pool:
                        def delete_adapters(entity):
                            try:
                                for adapter in entity['adapters']:
                                    if adapter.get('client_used') == local_client_id and \
                                            adapter[PLUGIN_NAME] == plugin_name:
                                        logger.debug('deleting ' + adapter['data']['id'])
                                        self.delete_adapter_entity(entity_type, adapter[PLUGIN_UNIQUE_NAME],
                                                                   adapter['data']['id'])
                            except Exception as e:
                                logger.exception(e)

                        pool.map(delete_adapters, entities_to_delete)
                        self._trigger('clear_dashboard_cache', blocking=False)

                # while we can quickly mark all adapters to be pending_delete
                # we still want to run a background task to delete them
                tmp_entity_type = entity_type
                run_and_forget(lambda: async_delete_entities(tmp_entity_type, entities_to_pass_to_be_deleted))

        self._trigger('clear_dashboard_cache', blocking=False)
        return client_from_db

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

    @gui_add_rule_logged_in('adapters/clients/labels', methods=['GET'])
    def adapters_client_labels(self) -> list:
        """
        :return: list of connection label mapping -> [{client_id,connection_label,plugin_uniq_name,node_id}} ]  instance
        """
        clients_label = []
        labels_from_db = self.adapter_client_labels_db.find({})
        for client in labels_from_db:
            client_id = client.get(CLIENT_ID)
            conn_label = client.get(CONNECTION_LABEL)
            plugin_name = client.get(PLUGIN_NAME)
            plugin_unique_name = client.get(PLUGIN_UNIQUE_NAME)
            if client_id and conn_label and plugin_name and plugin_unique_name:
                clients_label.append({'client_id': client_id,
                                      'label': conn_label,
                                      'plugin_name': plugin_name,
                                      'plugin_unique_name': plugin_unique_name})
            else:
                logger.error(f'invalid connection label , missing parameter {client_id}, {conn_label}, {plugin_name}')

        return jsonify(clients_label)
