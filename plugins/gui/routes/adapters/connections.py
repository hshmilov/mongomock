# pylint: disable=no-member,cell-var-from-loop,access-member-before-definition,too-many-locals,protected-access

import logging
import time
import json
import copy
from multiprocessing.pool import ThreadPool
from flask import (request, jsonify)
from bson import ObjectId

from axonius.adapter_base import AdapterBase
from axonius.consts.adapter_consts import LAST_FETCH_TIME, CLIENT_ID, CONNECTION_LABEL
from axonius.consts.gui_consts import (FeatureFlagsNames, IS_INSTANCES_MODE, INSTANCE_NAME, INSTANCE_PREV_NAME)
from axonius.consts.plugin_consts import (PLUGIN_NAME, PLUGIN_UNIQUE_NAME, NODE_ID, CONNECTION_DISCOVERY, CLIENT_ACTIVE)
from axonius.logging.audit_helper import AuditCategory
from axonius.plugin_base import return_error, EntityType
from axonius.utils.gui_helpers import (entity_fields)
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue
from axonius.utils.threading import run_and_forget
from gui.logic.login_helper import refill_passwords_fields, has_unchanged_password_value, remove_password_fields
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('<adapter_name>/connections', permission_section=PermissionCategory.Connections)
class Connections:

    @gui_route_logged_in(methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.Adapters))
    def get_adapter_connections_data(self, adapter_name):
        return jsonify(self._get_adapter_connections_data(adapter_name))

    @gui_route_logged_in(methods=['PUT'], activity_params=['adapter_name', 'client_id'], skip_activity=True)
    def add_connection(self, adapter_name):
        """
        Save and query assets for given connection data
        Request data is expected to contain the adapter name, instance id and connection parameters
        It may contain a label to name the connection

        :return: {
            id: <ObjectId of inserted document>
            status: <"success" or "error" of connection with give parameters>
            client_id: <calculated for the connection parameters, as defined by adapter>
        }
        """
        request_data = self.get_request_data_as_object()
        if not request_data:
            return return_error('Adapter name and connection data are required', 400)
        instance_id = request_data.pop('instance', self.node_id)
        is_instance_mode = request_data.pop(IS_INSTANCES_MODE, False)
        instance_name = request_data.pop(INSTANCE_NAME, '')
        connection_data = request_data
        if 'connection' not in request_data:
            connection_label = request_data.pop('connection_label', None)
            connection_data = {
                'connection': connection_data,
                'connection_label': connection_label
            }
        client_data, code = self._add_connection(adapter_name, instance_id, connection_data)

        if code == 200:
            try:
                client_id = json.loads(client_data).get(CLIENT_ID, '')
                self.log_activity_user_connection('put', adapter_name, client_id, instance_name, is_instance_mode)
            except Exception:
                logger.exception(f'error in audit message loading client_id from json client data {client_data}')
        return client_data, code

    @gui_route_logged_in('test', methods=['POST'], skip_activity=True)
    def test_connection(self, adapter_name):
        request_data = self.get_request_data_as_object()
        if not request_data:
            return return_error('Adapter name and connection data are required', 400)
        if request_data.get('instance'):
            instance_id = request_data.pop('instance', self.node_id)
        else:
            instance_id = request_data.pop('instanceName', self.node_id)
        connection_data = request_data.get('connection', request_data)
        return self._test_connection(adapter_name, instance_id, connection_data)

    @gui_route_logged_in('<connection_id>', methods=['POST', 'DELETE'], activity_params=['adapter_name', 'client_id'],
                         skip_activity=True)
    def update_connection(self, adapter_name, connection_id):
        request_data = self.get_request_data_as_object()
        if not request_data:
            return return_error('Adapter name and connection data are required', 400)
        is_instance_mode = request_data.pop(IS_INSTANCES_MODE, False)
        instance_name = request_data.pop(INSTANCE_NAME, '')
        instance_id = request_data.pop('instance') if request_data.get('instance')\
            else request_data.pop('instanceName', self.node_id)
        instance_prev_name = request_data.pop(INSTANCE_PREV_NAME) if request_data.get(INSTANCE_PREV_NAME)\
            else request_data.pop('oldInstanceName', None)
        instance_id_prev = request_data.pop('instance_prev', None)
        if request_data.get('connection'):
            connection_data = request_data
        else:
            connection_label = request_data.pop('connection_label', None)
            connection_active = request_data.pop('active', True)
            connection_data = {
                'connection': request_data,
                'connection_label': connection_label,
                'active': connection_active
            }

        return self._update_connection(connection_id, adapter_name, instance_id, instance_id_prev, connection_data,
                                       is_instance_mode, instance_name, instance_prev_name)

    def _add_connection(self, adapter_name, instance_id, connection_data):
        adapter_unique_name = self._get_adapter_unique_name(adapter_name, instance_id)

        def reset_cache_soon():
            time.sleep(5)
            entity_fields.clean_cache()

        if self._is_system_first_use:
            run_and_forget(reset_cache_soon())

        self._is_system_first_use = False
        return self._query_connection_for_devices(adapter_unique_name, connection_data)

    def _test_connection(self, adapter_name, instance_id, connection_data):
        if connection_data is None:
            return return_error('Invalid client', 400)

        adapter_unique_name = self._get_adapter_unique_name(adapter_name, instance_id)
        response = self.request_remote_plugin('client_test', adapter_unique_name, method='post',
                                              json=connection_data)
        if response is None:
            return 'Adapter is not responding', 400
        if response.status_code != 200:
            logger.error(f'Error in client adding: {response.status_code}, {response.text}')
        return response.text, response.status_code

    def _update_connection(self, connection_id, adapter_name, instance_id, prev_instance_id,
                           connection_data, is_instance_mode=False, instance_name='', instance_prev_name=''):
        try:
            adapter_unique_name = self._get_adapter_unique_name(adapter_name, prev_instance_id or instance_id)
        except Exception:
            raise ValueError(f'Adapter {adapter_name} with Instance {instance_id} or {prev_instance_id} not found')
        connection_from_db = self._get_collection('clients', adapter_unique_name).find_one({
            '_id': ObjectId(connection_id)
        })
        if not connection_from_db:
            return return_error('Server is already gone, please try again after refreshing the page')
        client_id = connection_from_db['client_id']
        if request.method == 'DELETE' and request.args.get('deleteEntities', False):
            self._remove_connection_assets(adapter_name, client_id)

        if request.method == 'DELETE':
            self.request_remote_plugin('clients/' + connection_id, adapter_unique_name, method='delete')
            self._adapters.clean_cache()
            self._adapters_v2.clean_cache()
            self.clients_labels.clean_cache()
            self._get_adapter_connections_data.clean_cache()
            self.log_activity_user_connection('delete', adapter_name, client_id, instance_name, is_instance_mode)
            return json.dumps({'client_id': client_id}), 200

        if not connection_data.get('connection'):
            return return_error('Connection data is required', 400)
        client_config = connection_from_db['client_config']
        connection_data[LAST_FETCH_TIME] = connection_from_db.get(LAST_FETCH_TIME)
        self._decrypt_client_config(client_config)
        could_fill_passwords = self._validate_fill_unchanged_passwords(adapter_unique_name, client_id,
                                                                       connection_data['connection'], client_config)
        should_reenter_credentials = self.feature_flags_config().get(FeatureFlagsNames.ReenterCredentials)
        if not could_fill_passwords and should_reenter_credentials:
            return return_error('Changing connection details requires re-entering credentials', 400)

        # for audit must get before old connection delete.
        client_label = self.adapter_client_labels_db.find_one({
            CLIENT_ID: client_id,
            PLUGIN_UNIQUE_NAME: adapter_unique_name,
            NODE_ID: prev_instance_id or instance_id
        }, {CONNECTION_LABEL: 1})

        self.request_remote_plugin('clients/' + connection_id, adapter_unique_name, method='delete')
        if prev_instance_id != instance_id:
            adapter_unique_name = self._get_adapter_unique_name(adapter_name, instance_id)

        # Audit client configuration changes
        try:
            adapter_schema = self._get_plugin_schemas(adapter_name).get('schema')

            # only audit discovery details in case it enabled
            def get_discovery_details(discovery: dict) -> dict:
                return discovery if discovery['enabled'] is True else {'enabled': False}

            def get_client_info(connection, label, discovery, active, instance):
                return {
                    'Connection': self._audit_remove_password_fields(adapter_schema, connection),
                    CONNECTION_LABEL: label or '',
                    'Discovery': get_discovery_details(discovery),
                    'Active': active,
                    'Instance_id': instance
                }

            connection_discovery_default = AdapterBase._connection_discovery_schema_default()
            # object to be updated
            current_client_info = get_client_info(client_config,
                                                  client_label.get(CONNECTION_LABEL) if client_label else None,
                                                  connection_from_db.get(CONNECTION_DISCOVERY,
                                                                         connection_discovery_default),
                                                  connection_from_db[CLIENT_ACTIVE],
                                                  prev_instance_id or instance_id)
            # object post updated
            updated_client_info = get_client_info(connection_data['connection'],
                                                  connection_data[CONNECTION_LABEL],
                                                  connection_data.get(CONNECTION_DISCOVERY,
                                                                      connection_discovery_default),
                                                  connection_data[CLIENT_ACTIVE],
                                                  instance_id)

            self.log_activity_user_default(AuditCategory.AdaptersConnections.value, 'post', {
                'adapter_name': adapter_name,
                CLIENT_ID: self._audit_get_client_with_node_name(client_id, is_instance_mode,
                                                                 instance_prev_name or instance_name),
                'current_client_info': json.dumps(current_client_info) or '',
                'updated_client_info': json.dumps(updated_client_info) or ''
            })

        except Exception:
            logger.exception('failed to audit adapter client connection changes')

        self._adapters.clean_cache()
        self._adapters_v2.clean_cache()
        self.clients_labels.clean_cache()
        self._get_adapter_connections_data.clean_cache()
        return self._query_connection_for_devices(adapter_unique_name, connection_data)

    def _remove_connection_assets(self, plugin_name, client_id):
        """
        Find all assets that came from given connection, mark them as 'pending_delete'
        and send async job to actually remove them

        :param plugin_name: Adapter name
        :param client_id: AD server or AWS Access Key
        :return:
        """
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
                                    'client_used': client_id
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
                            {'i.client_used': client_id}
                        ]
                    }
                ]
            )
            logger.info(f'Set pending_delete on {res.modified_count} axonius entities '
                        f'(or some adapters in them) from {res.matched_count} matches')
            assets_to_be_deleted = self._get_assets_to_delete(entity_type, plugin_name, client_id)

            def async_delete_entities(entity_type, entities_to_delete):
                with ThreadPool(5) as pool:
                    def delete_adapters(entity):
                        try:
                            for adapter in entity['adapters']:
                                if adapter.get('client_used') == client_id and \
                                        adapter[PLUGIN_NAME] == plugin_name:
                                    self.delete_adapter_entity(entity_type, adapter[PLUGIN_UNIQUE_NAME],
                                                               adapter['data']['id'])
                        except Exception as e:
                            logger.exception(e)

                    pool.map(delete_adapters, entities_to_delete)
                    self._trigger('clear_dashboard_cache', blocking=False)

            # while we can quickly mark all adapters to be pending_delete
            # we still want to run a background task to delete them
            tmp_entity_type = entity_type
            run_and_forget(lambda: async_delete_entities(tmp_entity_type, assets_to_be_deleted))
        self._trigger('clear_dashboard_cache', blocking=False)

    def _get_assets_to_delete(self, entity_type: EntityType, plugin_name: str, client_id: str):
        return list(self._entity_db_map[entity_type].find(
            {
                'adapters': {
                    '$elemMatch': {
                        '$and': [
                            {
                                PLUGIN_NAME: plugin_name
                            },
                            {
                                # and the device must be from this adapter
                                'client_used': client_id
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

    def _get_adapter_unique_name(self, adapter_name, instance_id):
        url = f'find_plugin_unique_name/nodes/{instance_id}/plugins/{adapter_name}'
        return self.request_remote_plugin(url).json().get('plugin_unique_name').json().get(PLUGIN_UNIQUE_NAME)

    def _query_connection_for_devices(self, adapter_unique_name, connection_data):
        if connection_data is None:
            return return_error('Invalid client', 400)

        save_and_fetch_connection = connection_data.pop('save_and_fetch', False)

        response = self.request_remote_plugin('clients', adapter_unique_name, 'put', json=connection_data)
        if not response:
            return return_error(f'Connection failure to adapter {adapter_unique_name}')

        self._adapters.clean_cache()
        self._adapters_v2.clean_cache()
        self._get_adapter_connections_data.clean_cache()
        self.clients_labels.clean_cache()

        if save_and_fetch_connection:
            if response.status_code == 200:
                self._client_insertion_threadpool.submit(self._fetch_after_clients_thread, adapter_unique_name,
                                                         response.json()['client_id'], connection_data)
            else:
                logger.error(f'Error in client adding: {response.status_code}, {response.text}')
        return response.text, response.status_code

    def _validate_fill_unchanged_passwords(self, adapter_unique_name: str, client_id: str, data: object,
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

    @staticmethod
    def _audit_remove_password_fields(adapter_schema: dict, client_config: dict) -> dict:
        """
        remove from client config field type password
        :param adapter_schema:
        :param client_config:
        :return: a clone of client config which is cleaned from passwords fields
        """
        audit_client_config = copy.deepcopy(client_config)
        remove_password_fields(adapter_schema, audit_client_config)
        return audit_client_config

    @staticmethod
    def _audit_get_client_with_node_name(client_id: str, is_instance_mode: bool, audit_instance_name: str) -> str:
        return f'{client_id} Node: {audit_instance_name}' if is_instance_mode else client_id

    def log_activity_user_connection(self, action: str, adapter_name: str, client_id: str,
                                     instance_name: str, is_instance_mode: bool):
        """
        audit client connection in case system at instances mode add to client_id the node name
        :param action: PUT,POST,DELETE
        :param adapter_name: the adapter name
        :param client_id: adapter client connection id
        :param instance_name: the node name map to node_id
        :param is_instance_mode: true if there are node connection,
        :return:
        """
        try:
            self.log_activity_user_default(AuditCategory.AdaptersConnections.value, action, {
                'adapter_name': adapter_name,
                CLIENT_ID: self._audit_get_client_with_node_name(client_id, is_instance_mode, instance_name)
            })
        except Exception:
            logger.exception(f'error in audit message with client_id {client_id}')
