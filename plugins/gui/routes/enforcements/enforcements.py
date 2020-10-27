import logging
from datetime import datetime

import pymongo
from bson import ObjectId
from flask import (jsonify,
                   request, Response)

from axonius.consts.gui_consts import (LAST_UPDATED_FIELD, UPDATED_BY_FIELD)
from axonius.consts.plugin_consts import (REPORTS_PLUGIN_NAME, DEVICE_CONTROL_PLUGIN_NAME)
from axonius.consts.report_consts import (ACTIONS_FAILURE_FIELD, ACTIONS_FIELD,
                                          ACTION_TYPE_FIELD,
                                          ACTIONS_MAIN_FIELD,
                                          ACTIONS_POST_FIELD,
                                          ACTIONS_SUCCESS_FIELD,
                                          LAST_TRIGGERED_FIELD,
                                          TIMES_TRIGGERED_FIELD,
                                          TRIGGERS_FIELD, ACTION_CONFIG_FIELD, ACTION_FIELD, TRIGGER_VIEW_NAME_FIELD,
                                          TRIGGER_RESULT_VIEW_NAME_FIELD, TRIGGER_PERIOD_FIELD, ACTION_NAME,
                                          ACTION_TYPE_DB_FIELD, ACTION_NAME_FIELD)

from axonius.plugin_base import EntityType, return_error
from axonius.utils.gui_helpers import (get_connected_user_id, paginated,
                                       filtered, sorted_endpoint,
                                       search_filter, metadata)
from axonius.utils.mongo_retries import mongo_retry
from axonius.utils.revving_cache import rev_cached
from gui.logic.api_helpers import get_page_metadata
from gui.logic.db_helpers import beautify_db_entry
from gui.logic.ec_helpers import extract_actions_from_ec
from gui.logic.login_helper import clear_passwords_fields, \
    refill_passwords_fields
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.routes.enforcements.tasks.tasks import Tasks

# pylint: disable=no-member

logger = logging.getLogger(f'axonius.{__name__}')


@gui_category_add_rules('enforcements')
class Enforcements(Tasks):

    def _get_enforcements(self, limit, mongo_filter, mongo_sort, skip, search: str = None):

        def beautify_enforcement(enforcement):
            actions = enforcement[ACTIONS_FIELD]
            trigger = enforcement[TRIGGERS_FIELD][0] if enforcement[TRIGGERS_FIELD] else None
            trigger_view_name = ''
            if trigger:
                trigger_view = trigger['view']
                trigger_view_entity = EntityType(trigger_view['entity'])
                trigger_view_name = self.common.data.find_view_name(trigger_view_entity, trigger_view['id'])

            main_action_type = self._get_action_type(actions[ACTIONS_MAIN_FIELD])
            return beautify_db_entry({
                '_id': enforcement['_id'], 'name': enforcement['name'],
                f'{ACTIONS_FIELD}.{ACTIONS_MAIN_FIELD}': actions[ACTIONS_MAIN_FIELD],
                f'{ACTIONS_FIELD}.{ACTIONS_MAIN_FIELD}.{ACTION_TYPE_FIELD}': main_action_type,
                TRIGGER_VIEW_NAME_FIELD: trigger_view_name,
                f'{TRIGGERS_FIELD}.{LAST_TRIGGERED_FIELD}': trigger.get(LAST_TRIGGERED_FIELD, '') if trigger else '',
                f'{TRIGGERS_FIELD}.{TIMES_TRIGGERED_FIELD}': trigger.get(TIMES_TRIGGERED_FIELD) if trigger else None,
                f'{TRIGGERS_FIELD}.{TRIGGER_PERIOD_FIELD}': trigger.get(TRIGGER_PERIOD_FIELD) if trigger else None,
                LAST_UPDATED_FIELD: enforcement.get(LAST_UPDATED_FIELD),
                UPDATED_BY_FIELD: enforcement.get(UPDATED_BY_FIELD)
            })

        if search:
            mongo_filter = {
                '$or': [
                    mongo_filter, {
                        'triggers.view.id': {
                            '$in': self.common.data.find_views_by_name_match(search)
                        }
                    }
                ]
            }
        enforcements = self.enforcements_collection.find(mongo_filter)
        if TRIGGER_VIEW_NAME_FIELD in mongo_sort:
            beautiful_enforcements = [beautify_enforcement(enforcement) for enforcement in enforcements]
            sorted_enforcements = sorted(beautiful_enforcements,
                                         key=lambda e: e[TRIGGER_VIEW_NAME_FIELD],
                                         reverse=mongo_sort[TRIGGER_VIEW_NAME_FIELD] == pymongo.DESCENDING)
            return sorted_enforcements[skip:(skip + limit)]
        sort = [(LAST_UPDATED_FIELD, pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())
        return [beautify_enforcement(enforcement) for enforcement in enforcements.sort(sort).skip(skip).limit(limit)]

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
        if not self.is_axonius_user():
            enforcement_to_add['user_id'] = str(get_connected_user_id())
            enforcement_to_add[LAST_UPDATED_FIELD] = datetime.now()
            enforcement_to_add[UPDATED_BY_FIELD] = get_connected_user_id()

        if enforcement_to_add[TRIGGERS_FIELD] and not enforcement_to_add[TRIGGERS_FIELD][0].get('name'):
            enforcement_to_add[TRIGGERS_FIELD][0]['name'] = enforcement_to_add['name']
        response = self.request_remote_plugin('reports', REPORTS_PLUGIN_NAME, method='put', json=enforcement_to_add,
                                              raise_on_network_error=True)
        if not response:
            return return_error(f'No response whether enforcement {enforcement_to_add["name"]} was saved', 400)

        self._trigger_remote_plugin(REPORTS_PLUGIN_NAME, 'process', data={
            'enforcement_id': response.text
        }, priority=True, blocking=False)
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
        return Response(response.text, response.status_code, mimetype='application/json')

    @paginated()
    @filtered()
    @sorted_endpoint()
    @search_filter()
    @metadata()
    @gui_route_logged_in(methods=['GET'])
    def get_enforcements(self, limit, skip, mongo_filter, mongo_sort, search, get_metadata: bool = True,
                         include_details: bool = False):
        """
        GET results in list of all currently configured enforcements, with their query id they were created with

        :return:
        """
        enforcements = self._get_enforcements(limit, mongo_filter, mongo_sort, skip, search=search)
        if get_metadata:
            return_doc = {
                'page': get_page_metadata(skip, limit, len(enforcements)),
                'assets': enforcements
            }
            return jsonify(return_doc)
        return jsonify(enforcements)

    @gui_route_logged_in(methods=['PUT'])
    def add_enforcements(self):
        """
        PUT Send report_service a new enforcement to be configured

        :return:
        """
        enforcement_to_add = request.get_json(silent=True)
        return self.put_enforcement({
            'name': enforcement_to_add['name'],
            ACTIONS_FIELD: enforcement_to_add[ACTIONS_FIELD],
            TRIGGERS_FIELD: enforcement_to_add[TRIGGERS_FIELD]
        })

    @gui_route_logged_in(methods=['DELETE'], activity_params=['deleted'])
    def delete_enforcements(self):
        """
        DELETE delete an enforcement

        :return:
        """
        enforcement_selection = self.get_request_data_as_object()
        if isinstance(enforcement_selection, list):
            enforcement_selection = {
                'ids': enforcement_selection,
                'include': True
            }
        return self.delete_enforcement(enforcement_selection)

    @filtered()
    @gui_route_logged_in('count')
    def enforcements_count(self, mongo_filter):
        return jsonify(self.enforcements_collection.count_documents(mongo_filter))

    @gui_route_logged_in('saved')
    def saved_enforcements(self):
        """
        Returns a list of all existing Saved Enforcement names, in order to check duplicates
        """
        return jsonify([x['name'] for x in self.enforcements_collection.find({}, {
            'name': 1
        })])

    @gui_route_logged_in('<enforcement_id>', methods=['GET'])
    def get_enforcement_by_id(self, enforcement_id):
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

    @gui_route_logged_in('<enforcement_id>', methods=['POST'])
    def update_enforcement_by_id(self, enforcement_id):
        enforcement_data = request.get_json(silent=True)
        enforcement_to_update = {
            'name': enforcement_data['name'],
            ACTIONS_FIELD: enforcement_data[ACTIONS_FIELD],
            TRIGGERS_FIELD: enforcement_data[TRIGGERS_FIELD]
        }
        if not self.is_axonius_user():
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

        self._trigger_remote_plugin(REPORTS_PLUGIN_NAME, 'process', data={
            'enforcement_id': enforcement_id
        }, priority=True, blocking=False)

        return Response(response.text, response.status_code, mimetype='application/json')

    @gui_route_logged_in('<enforcement_id>/trigger', methods=['POST'], proceed_and_set_access=True)
    def trigger_enforcement_by_id(self, enforcement_id, no_access):
        """
        Triggers a job for the requested enforcement with its first trigger
        """

        # If there are no permissions, also check that the request doesn't relate to the enforcement page run
        # Only then we report error and exit
        if no_access and not request.get_json().get('ec_page_run'):
            return return_error('You are lacking some permissions for this request', 401)

        enforcement = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        }, {
            'name': 1,
            TRIGGERS_FIELD: 1
        })
        self._trigger_remote_plugin(REPORTS_PLUGIN_NAME, 'run', data={
            'report_name': enforcement['name'],
            'configuration_name': enforcement[TRIGGERS_FIELD][0]['name'],
            'manual': True
        }, priority=True, blocking=False)
        return jsonify({
            'name': enforcement['name']
        })

    @gui_route_logged_in('<entity_type>/custom', methods=['POST'], enforce_permissions=False,
                         support_internal_api_key=True)
    def enforce_entity_custom_data(self, entity_type):
        """
        See self._entity_custom_data
        """
        logger.info('Adding Custom Data by Triggered Enforcement')
        return self._entity_custom_data(EntityType(entity_type))

    @rev_cached(ttl=3600)
    def _get_actions_from_reports_plugin(self) -> dict:
        response = self.request_remote_plugin('reports/actions', REPORTS_PLUGIN_NAME,
                                              method='get', raise_on_network_error=True)
        response.raise_for_status()
        return response.json()

    @gui_route_logged_in('cache/<cache_name>/delete')
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

    @gui_route_logged_in('actions')
    def actions(self):
        """
        Returns all action names and their schema, as defined by the author of the class
        """
        response = self._get_actions_from_reports_plugin()

        return jsonify(response)

    @gui_route_logged_in('actions/saved')
    def saved_actions(self):
        """
        Returns a list of all existing Saved Action names, in order to check duplicates
        """
        return jsonify([x['name'] for x in self.enforcements_saved_actions_collection.find({}, {
            'name': 1
        })])

    @paginated()
    @filtered()
    @sorted_endpoint()
    @search_filter()
    @gui_route_logged_in('<enforcement_id>/tasks', methods=['GET'])
    def tasks_by_enforcement_id(self, enforcement_id, limit, skip, mongo_filter, mongo_sort, search):
        enforcement = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        })
        if not enforcement:
            return return_error(f'Enforcement with id {enforcement_id} was not found', 400)

        if mongo_sort.get('status'):
            mongo_sort['job_completed_state'] = -1 * mongo_sort['status']
            del mongo_sort['status']
        tasks = self.enforcement_tasks_runs_collection.find(
            self._tasks_query(mongo_filter, enforcement['name'], search))
        if TRIGGER_RESULT_VIEW_NAME_FIELD in mongo_sort:
            beautiful_tasks = [self.beautify_task_entry(task) for task in tasks]
            sorted_tasks = sorted(beautiful_tasks, key=lambda e: e[TRIGGER_RESULT_VIEW_NAME_FIELD],
                                  reverse=mongo_sort[TRIGGER_RESULT_VIEW_NAME_FIELD] == pymongo.DESCENDING)
            return jsonify(sorted_tasks[skip: (skip + limit)])
        sort = [('finished_at', pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())
        return jsonify([self.beautify_task_entry(x) for x in tasks.sort(sort).skip(skip).limit(limit)])

    @filtered()
    @gui_route_logged_in('<enforcement_id>/tasks/count', methods=['GET'])
    def tasks_by_enforcement_id_count(self, enforcement_id, mongo_filter):
        enforcement = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        })
        if not enforcement:
            return return_error(f'Enforcement with id {enforcement_id} was not found', 400)

        return jsonify(self.enforcement_tasks_runs_collection.count_documents(
            self._tasks_query(mongo_filter, enforcement['name'])
        ))

    @gui_route_logged_in('actions/upload_file', methods=['POST'], skip_activity=True)
    def actions_upload_file(self):
        return self._upload_file(DEVICE_CONTROL_PLUGIN_NAME)

    def _get_action_type(self, action_name):
        action = self.enforcements_saved_actions_collection.find_one({
            ACTION_NAME: action_name
        }, {
            ACTION_TYPE_DB_FIELD: 1
        })
        if not action:
            logger.info(f'Requested action {action_name} not found')
            return ''
        return action.get(ACTION_FIELD, {}).get(ACTION_NAME_FIELD, '')
