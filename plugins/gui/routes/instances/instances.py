import logging

from flask import (jsonify)

from axonius.consts import adapter_consts
from axonius.consts.core_consts import ACTIVATED_NODE_STATUS, DEACTIVATED_NODE_STATUS
from axonius.consts.plugin_consts import (NODE_ID, NODE_NAME, NODE_HOSTNAME,
                                          PLUGIN_NAME, PLUGIN_UNIQUE_NAME, NODE_DATA_INSTANCE_ID, NODE_STATUS,
                                          NODE_USE_AS_ENV_NAME)
from axonius.logging.audit_helper import AuditCategory
from axonius.plugin_base import return_error
from axonius.utils.permissions_helper import (PermissionCategory, PermissionAction, PermissionValue)
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in, is_valid_node_hostname

# pylint: disable=no-member,too-many-boolean-expressions,inconsistent-return-statements,no-else-return,too-many-branches

logger = logging.getLogger(f'axonius.{__name__}')


@gui_category_add_rules('instances')
class Instances:

    @gui_route_logged_in(methods=['GET'])
    def get_instances(self):
        db_connection = self._get_db_connection()
        nodes = self._get_nodes_table()
        system_config = db_connection['gui']['system_collection'].find_one({'type': 'server'}) or {}
        connection_key = None
        user_instances_permission = self.get_user_permissions().get(PermissionCategory.Instances)
        if (user_instances_permission and user_instances_permission[PermissionAction.Update]) or self.is_admin_user():
            connection_key = self.encryption_key
        return jsonify({
            'instances': nodes,
            'connection_data': {
                'key': connection_key,
                'host': system_config.get('server_name', '<axonius-hostname>')
            }
        })

    def update_instance(self, instance_data, attributes):
        for attribute in attributes:
            if instance_data.get(attribute, None) is not None:
                node_id = instance_data.get(NODE_DATA_INSTANCE_ID)
                self._log_activity_instances(instance_data, attribute)
                self.request_remote_plugin(f'node/{node_id}', method='POST',
                                           json={'key': attribute, 'value': instance_data.get(attribute)})
            else:
                logger.error(f'{attribute} is null - wrong parameters. ')

    @gui_route_logged_in(methods=['POST'], skip_activity=True)
    def update_instances(self):
        data = self.get_request_data_as_object()

        # REACTIVATE NODE
        if NODE_DATA_INSTANCE_ID in data and NODE_STATUS in data:
            self.update_instance(instance_data=data, attributes=[NODE_STATUS])
        # UPDATE NODE NAME AND HOSTNAME
        elif NODE_DATA_INSTANCE_ID in data:
            self.update_instance(instance_data=data, attributes=[NODE_NAME, NODE_USE_AS_ENV_NAME])
            self._get_environment_name.update_cache()
            if is_valid_node_hostname(data[NODE_HOSTNAME]):
                if self._update_hostname_on_node(instance_data=data):
                    self.update_instance(instance_data=data, attributes=[NODE_HOSTNAME])
                else:
                    return return_error(f'Failed to change hostname', 400)
            else:
                return return_error(f'Illegal hostname value entered', 400)
        return ''

    @gui_route_logged_in(methods=['DELETE'],
                         required_permission=PermissionValue.get(PermissionAction.Update, PermissionCategory.Instances),
                         skip_activity=True)
    def delete_instances(self):
        data = self.get_request_data_as_object()
        node_ids = data[NODE_DATA_INSTANCE_ID]
        if self.node_id in node_ids:
            return return_error('Can\'t Deactivate Master.', 400)

        for current_node in node_ids:
            # List because it might take a while for the process to finish
            # and cursors have a TTL
            node_adapters = list(self.core_configs_collection.find({
                'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE,
                NODE_ID: current_node
            }, projection={
                PLUGIN_UNIQUE_NAME: True,
                PLUGIN_NAME: True
            }))

            for adapter in node_adapters:
                plugin_unique_name = adapter[PLUGIN_UNIQUE_NAME]
                plugin_name = adapter[PLUGIN_NAME]
                cursor = self._get_collection('clients', plugin_unique_name).find({},
                                                                                  projection={'_id': 1})
                for current_client in cursor:
                    self.request_remote_plugin(
                        'clients/' + str(current_client['_id']), plugin_unique_name, method='delete')

            # Deactivate node
            deactivated_data = {'key': 'status', 'value': DEACTIVATED_NODE_STATUS}
            self.request_remote_plugin(f'node/{current_node}', method='POST', json=deactivated_data)
            self._log_activity_instances(instance_data={NODE_DATA_INSTANCE_ID: current_node,
                                                        NODE_STATUS: DEACTIVATED_NODE_STATUS},
                                         attributes=NODE_STATUS)
        return ''

    def _is_node_activated(self, target_node_id=None) -> bool:

        if target_node_id == self.node_id:
            logger.debug(f'node id {target_node_id} is The MASTER ')
            return True

        node = self._nodes_metadata_collection.find_one({NODE_ID: target_node_id})

        if node is None or not node.get(NODE_STATUS, ACTIVATED_NODE_STATUS) == ACTIVATED_NODE_STATUS:
            logger.error(f'node id {target_node_id} is not Activated ')
            return False
        logger.debug(f'node id {target_node_id} is online  ')
        return True

    def _update_hostname_on_node(self, instance_data=None):
        node_id = instance_data.get(NODE_DATA_INSTANCE_ID, None)
        logger.info(f'Starting to update hostname for target node id {node_id}')
        new_hostname = str(instance_data.get(NODE_HOSTNAME))

        url = f'find_plugin_unique_name/nodes/{node_id}/plugins/instance_control'
        node_unique_name_response = self.request_remote_plugin(url)
        if not node_unique_name_response.text:
            logger.error(f'Unable to retrieve plugin_unique_name for id {node_id}')
            return False

        node_unique_name = node_unique_name_response.json().get('plugin_unique_name')

        if node_unique_name is None:
            logger.error(f'unable to allocate target instance control plugin_unique_name with id  {node_id}')
            return False

        if self._is_node_activated(node_id) and node_unique_name:
            resp = self.request_remote_plugin(f'instances/host/{new_hostname}',
                                              node_unique_name,
                                              method='put',
                                              raise_on_network_error=True)
            if resp.status_code != 200:
                logger.error(f'failure to update node hostname response '
                             f'back from instance control {str(resp.content)} ')
            else:
                return True
        else:
            logger.error('node is offline aborting hostname update')
        return False

    @gui_route_logged_in('tags', methods=['POST'])
    def update_instances_tags(self):
        data = self.get_request_data_as_object()
        self.request_remote_plugin(f'nodes/tags/{data["node_id"]}', method='POST', json={'tags': data['tags']})
        return ''

    @gui_route_logged_in('tags', methods=['DELETE'], required_permission=PermissionValue.get(
        PermissionAction.Update, PermissionCategory.Instances))
    def delete_instances_tags(self):
        data = self.get_request_data_as_object()
        self.request_remote_plugin(f'nodes/tags/{data["node_id"]}', method='DELETE', json={'tags': data['tags']})
        return ''

    def _log_activity_instances(self, instance_data: dict, attributes: str):
        def audit(action: str, params: dict):
            self.log_activity_user_default(AuditCategory.Instances.value, action, params)

        try:
            if attributes and instance_data:
                node = self._nodes_metadata_collection.find_one({NODE_ID: instance_data.get(NODE_DATA_INSTANCE_ID)})

            if not node:
                logger.warning(f'Skipping audit for node id {NODE_DATA_INSTANCE_ID}')
                return

            if NODE_STATUS in attributes:
                audit(action='node_update_status', params={
                    NODE_NAME: node.get(NODE_NAME, ''),
                    NODE_STATUS: instance_data.get(NODE_STATUS, '')
                })

            if NODE_HOSTNAME in attributes and instance_data.get(NODE_HOSTNAME) != node.get(NODE_HOSTNAME):
                audit(action='node_update_hostname', params={
                    NODE_NAME: node.get(NODE_NAME, ''),
                    NODE_HOSTNAME: node.get(NODE_HOSTNAME, ''),
                    f'update_{NODE_HOSTNAME}': instance_data.get(NODE_HOSTNAME, '')
                })

            if NODE_NAME in attributes and instance_data.get(NODE_NAME) != node.get(NODE_NAME):
                audit(action='node_update_name', params={
                    NODE_NAME: node.get(NODE_NAME, ''),
                    f'update_{NODE_NAME}': instance_data.get(NODE_NAME, '')
                })

            if NODE_USE_AS_ENV_NAME in attributes and \
                    instance_data.get(NODE_USE_AS_ENV_NAME) != node.get(NODE_USE_AS_ENV_NAME, False):
                audit(action='node_update_indication', params={
                    NODE_NAME: node.get(NODE_NAME, ''),
                    f'update_indication': 'enabled' if instance_data.get(NODE_USE_AS_ENV_NAME) else 'disabled'
                })

        except Exception:
            logger.exception(f'error during instances auditing')
