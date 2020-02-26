import logging
from datetime import datetime

import pymongo
from bson import ObjectId
from flask import (jsonify,
                   request)

from axonius.consts.gui_consts import (LAST_UPDATED_FIELD, UPDATED_BY_FIELD)
from axonius.consts.plugin_consts import (REPORTS_PLUGIN_NAME)
from axonius.consts.report_consts import (ACTIONS_FAILURE_FIELD, ACTIONS_FIELD,
                                          ACTIONS_MAIN_FIELD,
                                          ACTIONS_POST_FIELD,
                                          ACTIONS_SUCCESS_FIELD,
                                          LAST_TRIGGERED_FIELD,
                                          TIMES_TRIGGERED_FIELD,
                                          TRIGGERS_FIELD, ACTION_CONFIG_FIELD, ACTION_FIELD)
from axonius.plugin_base import EntityType, return_error, add_rule
from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType, ReadOnlyJustForGet,
                                       get_connected_user_id, paginated,
                                       filtered, sorted_endpoint)
from axonius.utils.mongo_retries import mongo_retry
from axonius.utils.revving_cache import rev_cached
from gui.logic.db_helpers import beautify_db_entry
from gui.logic.ec_helpers import extract_actions_from_ec
from gui.logic.login_helper import clear_passwords_fields, \
    refill_passwords_fields
from gui.logic.routing_helper import gui_add_rule_logged_in
from gui.routes.enforcements.tasks.tasks import Tasks
# pylint: disable=no-member

logger = logging.getLogger(f'axonius.{__name__}')


class Enforcements(Tasks):

    def get_enforcements(self, limit, mongo_filter, mongo_sort, skip):
        sort = [(LAST_UPDATED_FIELD, pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())

        def beautify_enforcement(enforcement):
            actions = enforcement[ACTIONS_FIELD]
            trigger = enforcement[TRIGGERS_FIELD][0] if enforcement[TRIGGERS_FIELD] else None
            return beautify_db_entry({
                '_id': enforcement['_id'], 'name': enforcement['name'],
                f'{ACTIONS_FIELD}.{ACTIONS_MAIN_FIELD}': actions[ACTIONS_MAIN_FIELD],
                f'{TRIGGERS_FIELD}.view.name': trigger['view']['name'] if trigger else '',
                f'{TRIGGERS_FIELD}.{LAST_TRIGGERED_FIELD}': trigger.get(LAST_TRIGGERED_FIELD, '') if trigger else '',
                f'{TRIGGERS_FIELD}.{TIMES_TRIGGERED_FIELD}': trigger.get(TIMES_TRIGGERED_FIELD) if trigger else None,
                LAST_UPDATED_FIELD: enforcement.get(LAST_UPDATED_FIELD),
                UPDATED_BY_FIELD: enforcement.get(UPDATED_BY_FIELD)
            })

        return [beautify_enforcement(enforcement) for enforcement in self.enforcements_collection.find(
            mongo_filter).sort(sort).skip(skip).limit(limit)]

    def __process_enforcement_actions(self, actions):
        # This is a transitional method, i.e. it's here to maximize compatibility with previous versions
        @mongo_retry()
        def create_saved_action(action) -> str:
            """
            Create a saved action from the given action and returns its name
            """
            if not action or not action.get('name'):
                return ''
            self._encrypt_client_config(action.get(ACTION_FIELD, {}).get(ACTION_CONFIG_FIELD, {}))
            with self.enforcements_saved_actions_collection.start_session() as transaction:
                if 'uuid' in action:
                    del action['uuid']
                    del action['date_fetched']
                transaction.insert_one(action)
                return action['name']

        actions[ACTIONS_MAIN_FIELD] = create_saved_action(actions[ACTIONS_MAIN_FIELD])
        actions[ACTIONS_SUCCESS_FIELD] = [create_saved_action(x) for x in actions.get(ACTIONS_SUCCESS_FIELD) or []]
        actions[ACTIONS_FAILURE_FIELD] = [create_saved_action(x) for x in actions.get(ACTIONS_FAILURE_FIELD) or []]
        actions[ACTIONS_POST_FIELD] = [create_saved_action(x) for x in actions.get(ACTIONS_POST_FIELD) or []]

    def put_enforcement(self, enforcement_to_add):
        self.__process_enforcement_actions(enforcement_to_add[ACTIONS_FIELD])
        if not self._is_hidden_user():
            enforcement_to_add['user_id'] = str(get_connected_user_id())
            enforcement_to_add[LAST_UPDATED_FIELD] = datetime.now()
            enforcement_to_add[UPDATED_BY_FIELD] = get_connected_user_id()

        if enforcement_to_add[TRIGGERS_FIELD] and not enforcement_to_add[TRIGGERS_FIELD][0].get('name'):
            enforcement_to_add[TRIGGERS_FIELD][0]['name'] = enforcement_to_add['name']
        response = self.request_remote_plugin('reports', REPORTS_PLUGIN_NAME, method='put', json=enforcement_to_add,
                                              raise_on_network_error=True)
        return response.text, response.status_code

    def delete_enforcement(self, enforcement_selection):
        # Since other method types cause the function to return - here we have DELETE request
        if enforcement_selection is None or (not enforcement_selection.get('ids')
                                             and enforcement_selection.get('include')):
            logger.error('No enforcement provided to be deleted')
            return ''

        response = self.request_remote_plugin('reports', REPORTS_PLUGIN_NAME, method='DELETE',
                                              json=enforcement_selection['ids'] if enforcement_selection['include']
                                              else [
                                                  str(report['_id']) for report in self.enforcements_collection.find({
                                                      '_id': {
                                                          '$nin': [ObjectId(x) for x in enforcement_selection['ids']]
                                                      }
                                                  }, projection={'_id': 1})])
        if response is None:
            return return_error('No response whether enforcement was removed')
        return response.text, response.status_code

    @paginated()
    @filtered()
    @sorted_endpoint()
    @gui_add_rule_logged_in('enforcements', methods=['GET', 'PUT', 'DELETE'],
                            required_permissions={Permission(PermissionType.Enforcements,
                                                             ReadOnlyJustForGet)})
    def enforcements(self, limit, skip, mongo_filter, mongo_sort):
        """
        GET results in list of all currently configured enforcements, with their query id they were created with
        PUT Send report_service a new enforcement to be configured

        :return:
        """
        if request.method == 'GET':
            return jsonify(self.get_enforcements(limit, mongo_filter, mongo_sort, skip))

        if request.method == 'PUT':
            enforcement_to_add = request.get_json(silent=True)
            return self.put_enforcement({
                'name': enforcement_to_add['name'],
                ACTIONS_FIELD: enforcement_to_add[ACTIONS_FIELD],
                TRIGGERS_FIELD: enforcement_to_add[TRIGGERS_FIELD]
            })

        # Handle remaining method - DELETE
        return self.delete_enforcement(self.get_request_data_as_object())

    @filtered()
    @gui_add_rule_logged_in('enforcements/count', required_permissions={Permission(PermissionType.Enforcements,
                                                                                   PermissionLevel.ReadOnly)})
    def enforcements_count(self, mongo_filter):
        return jsonify(self.enforcements_collection.count_documents(mongo_filter))

    @gui_add_rule_logged_in('enforcements/saved', required_permissions={Permission(PermissionType.Enforcements,
                                                                                   PermissionLevel.ReadOnly)})
    def saved_enforcements(self):
        """
        Returns a list of all existing Saved Enforcement names, in order to check duplicates
        """
        return jsonify([x['name'] for x in self.enforcements_collection.find({}, {
            'name': 1
        })])

    @gui_add_rule_logged_in('enforcements/<enforcement_id>', methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Enforcements,
                                                             ReadOnlyJustForGet)})
    def enforcement_by_id(self, enforcement_id):
        if request.method == 'GET':
            def get_saved_action(name):
                if not name:
                    return {}
                saved_action = self.enforcements_saved_actions_collection.find_one({
                    'name': name
                })
                if not saved_action:
                    return {}
                self._decrypt_client_config(saved_action.get(ACTION_FIELD, {}).get(ACTION_CONFIG_FIELD, {}))
                # fixing password to be 'unchanged'
                action_type = saved_action['action']['action_name']
                schema = self._get_actions_from_reports_plugin()[action_type]['schema']
                saved_action['action']['config'] = clear_passwords_fields(saved_action['action']['config'], schema)
                return beautify_db_entry(saved_action)

            enforcement = self.enforcements_collection.find_one({
                '_id': ObjectId(enforcement_id)
            }, {
                'name': 1,
                ACTIONS_FIELD: 1,
                TRIGGERS_FIELD: 1
            })
            if not enforcement:
                return return_error(f'Enforcement with id {enforcement_id} was not found', 400)

            actions = enforcement[ACTIONS_FIELD]
            actions[ACTIONS_MAIN_FIELD] = get_saved_action(actions[ACTIONS_MAIN_FIELD])
            actions[ACTIONS_SUCCESS_FIELD] = [get_saved_action(x) for x in actions.get(ACTIONS_SUCCESS_FIELD) or []]
            actions[ACTIONS_FAILURE_FIELD] = [get_saved_action(x) for x in actions.get(ACTIONS_FAILURE_FIELD) or []]
            actions[ACTIONS_POST_FIELD] = [get_saved_action(x) for x in actions.get(ACTIONS_POST_FIELD) or []]

            for trigger in enforcement[TRIGGERS_FIELD]:
                trigger['id'] = trigger['name']
            return jsonify(beautify_db_entry(enforcement))

        # Handle remaining request - POST
        enforcement_data = request.get_json(silent=True)
        enforcement_to_update = {
            'name': enforcement_data['name'],
            ACTIONS_FIELD: enforcement_data[ACTIONS_FIELD],
            TRIGGERS_FIELD: enforcement_data[TRIGGERS_FIELD]
        }
        if not self._is_hidden_user():
            enforcement_to_update[LAST_UPDATED_FIELD] = datetime.now()
            enforcement_to_update[UPDATED_BY_FIELD] = get_connected_user_id()

        enforcement_actions_from_user = {
            x['name']: x
            for x
            in extract_actions_from_ec(enforcement_to_update['actions'])
        }

        # Remove old enforcement's actions
        enforcement_actions = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        }, {
            'actions': 1
        })['actions']

        all_actions_from_db = extract_actions_from_ec(enforcement_actions)

        all_actions_query = {
            'name': {
                '$in': all_actions_from_db
            }
        }

        for action_from_db in self.enforcements_saved_actions_collection.find(all_actions_query,
                                                                              projection={
                                                                                  'name': 1,
                                                                                  'action.config': 1,
                                                                                  '_id': 0
                                                                              }):
            corresponding_user_action = enforcement_actions_from_user.get(action_from_db['name'])
            self._decrypt_client_config(action_from_db.get(ACTION_FIELD, {}).get(ACTION_CONFIG_FIELD, {}))
            logger.debug(action_from_db)
            logger.debug(corresponding_user_action)
            if not corresponding_user_action:
                continue
            corresponding_user_action['action']['config'] = refill_passwords_fields(
                corresponding_user_action['action']['config'],
                action_from_db['action']['config'])

        self.enforcements_saved_actions_collection.delete_many(all_actions_query)

        self.__process_enforcement_actions(enforcement_to_update[ACTIONS_FIELD])
        response = self.request_remote_plugin(f'reports/{enforcement_id}', REPORTS_PLUGIN_NAME, method='post',
                                              json=enforcement_to_update)
        if response is None:
            return return_error('No response whether enforcement was updated')

        for trigger in enforcement_to_update['triggers']:
            trigger_res = self.request_remote_plugin(f'reports/{enforcement_id}/{trigger.get("id", trigger["name"])}',
                                                     REPORTS_PLUGIN_NAME, method='post', json=trigger)
            if trigger_res is None or trigger_res.status_code == 500:
                logger.error(f'Failed to save trigger {trigger["name"]}')

        return response.text, response.status_code

    @gui_add_rule_logged_in('enforcements/<enforcement_id>/trigger', methods=['POST'],
                            required_permissions={Permission(PermissionType.Enforcements, PermissionLevel.ReadWrite)})
    def trigger_enforcement_by_id(self, enforcement_id):
        """
        Triggers a job for the requested enforcement with its first trigger
        """

        enforcement = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        }, {
            'name': 1,
            TRIGGERS_FIELD: 1
        })
        response = self._trigger_remote_plugin(REPORTS_PLUGIN_NAME, 'run', data={
            'report_name': enforcement['name'],
            'configuration_name': enforcement[TRIGGERS_FIELD][0]['name'],
            'manual': True
        }, priority=True)
        return response.text, response.status_code

    @add_rule('enforcements/<entity_type>/custom', methods=['POST'])
    def enforce_entity_custom_data(self, entity_type):
        """
        See self._entity_custom_data
        """
        return self._entity_custom_data(EntityType(entity_type))

    @rev_cached(ttl=3600)
    def _get_actions_from_reports_plugin(self) -> dict:
        response = self.request_remote_plugin('reports/actions', REPORTS_PLUGIN_NAME,
                                              method='get', raise_on_network_error=True)
        response.raise_for_status()
        return response.json()

    @gui_add_rule_logged_in('cache/<cache_name>/delete')
    def _clean_cache(self, cache_name):
        if cache_name == 'reports_actions':
            logger.info('Cleaning _get_actions_from_reports_plugin cache async...')
            try:
                self._get_actions_from_reports_plugin.update_cache()
            except Exception as e:
                logger.exception(f'Exception while cleaning cache for {cache_name}')
                return jsonify({'status': False, 'exception': str(e)})
            return jsonify({'status': True})

        return jsonify({'status': False})

    @gui_add_rule_logged_in('enforcements/actions', required_permissions={Permission(PermissionType.Enforcements,
                                                                                     PermissionLevel.ReadOnly)})
    def actions(self):
        """
        Returns all action names and their schema, as defined by the author of the class
        """
        response = self._get_actions_from_reports_plugin()

        return jsonify(response)

    @gui_add_rule_logged_in('enforcements/actions/saved', required_permissions={Permission(PermissionType.Enforcements,
                                                                                           PermissionLevel.ReadOnly)})
    def saved_actions(self):
        """
        Returns a list of all existing Saved Action names, in order to check duplicates
        """
        return jsonify([x['name'] for x in self.enforcements_saved_actions_collection.find({}, {
            'name': 1
        })])
