import logging

import pymongo
from bson import ObjectId
from flask import (jsonify)

from axonius.consts.report_consts import (ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD,
                                          ACTIONS_SUCCESS_FIELD,
                                          NOT_RAN_STATE)
from axonius.mixins.triggerable import (StoredJobStateCompletion)
from axonius.plugin_base import return_error
from axonius.consts.report_consts import (ACTIONS_MAIN_FIELD)
from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType, paginated,
                                       filtered, sorted_endpoint)
from axonius.utils.mongo_chunked import get_chunks_length
from gui.logic.db_helpers import beautify_db_entry
from gui.logic.entity_data import (get_task_full_name)
from gui.logic.login_helper import clear_passwords_fields
from gui.logic.routing_helper import gui_add_rule_logged_in
# pylint: disable=no-member

logger = logging.getLogger(f'axonius.{__name__}')


class Tasks:
    @paginated()
    @filtered()
    @sorted_endpoint()
    @gui_add_rule_logged_in('enforcements/<enforcement_id>/tasks', methods=['GET'],
                            required_permissions={Permission(PermissionType.Enforcements, PermissionLevel.ReadOnly)})
    def tasks_by_enforcement_id(self, enforcement_id, limit, skip, mongo_filter, mongo_sort):
        enforcement = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        })
        if not enforcement:
            return return_error(f'Enforcement with id {enforcement_id} was not found', 400)

        if mongo_sort.get('status'):
            mongo_sort['job_completed_state'] = -1 * mongo_sort['status']
            del mongo_sort['status']
        sort = [('finished_at', pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())
        return jsonify([self.beautify_task_entry(x) for x in self.enforcement_tasks_runs_collection.find(
            self._tasks_query(mongo_filter, enforcement['name'])).sort(sort).skip(skip).limit(limit)])

    @filtered()
    @gui_add_rule_logged_in('enforcements/<enforcement_id>/tasks/count', methods=['GET'],
                            required_permissions={Permission(PermissionType.Enforcements, PermissionLevel.ReadOnly)})
    def tasks_by_enforcement_id_count(self, enforcement_id, mongo_filter):
        enforcement = self.enforcements_collection.find_one({
            '_id': ObjectId(enforcement_id)
        })
        if not enforcement:
            return return_error(f'Enforcement with id {enforcement_id} was not found', 400)

        return jsonify(self.enforcement_tasks_runs_collection.count_documents(
            self._tasks_query(mongo_filter, enforcement['name'])
        ))

    @staticmethod
    def _tasks_query(mongo_filter, enforcement_name=None):
        """
        General query for all Complete / In progress task that also answer given mongo_filter
        """
        query_segments = [{
            'job_name': 'run',
            '$or': [
                {
                    'job_completed_state': StoredJobStateCompletion.Successful.name,
                    'result': {
                        '$ne': NOT_RAN_STATE
                    }
                }, {
                    'job_completed_state': StoredJobStateCompletion.Running.name
                }
            ]
        }, mongo_filter]

        if enforcement_name:
            query_segments.append({
                'post_json.report_name': enforcement_name
            })

        return {
            '$and': query_segments
        }

    @paginated()
    @filtered()
    @sorted_endpoint()
    @gui_add_rule_logged_in('tasks', required_permissions={Permission(PermissionType.Enforcements,
                                                                      PermissionLevel.ReadOnly)})
    def enforcement_tasks(self, limit, skip, mongo_filter, mongo_sort):

        if mongo_sort.get('status'):
            mongo_sort['job_completed_state'] = -1 * mongo_sort['status']
            del mongo_sort['status']
        sort = [('finished_at', pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())
        return jsonify([self.beautify_task_entry(x) for x in self.enforcement_tasks_runs_collection.find(
            self._tasks_query(mongo_filter)).sort(sort).skip(skip).limit(limit)])

    @filtered()
    @gui_add_rule_logged_in('tasks/count', required_permissions={Permission(PermissionType.Enforcements,
                                                                            PermissionLevel.ReadOnly)})
    def enforcement_tasks_count(self, mongo_filter):
        """
        Counts how many 'run' tasks are documented in the trigger history of reports plugin
        """
        return jsonify(self.enforcement_tasks_runs_collection.count_documents(self._tasks_query(mongo_filter)))

    @gui_add_rule_logged_in('tasks/<task_id>', required_permissions={Permission(PermissionType.Enforcements,
                                                                                PermissionLevel.ReadOnly)})
    def enforcement_task_by_id(self, task_id):
        """
        Fetch an entire 'run' record with all its results, according to given task_id
        """

        def beautify_task(task):
            """
            Find the configuration that triggered this task and merge its details with task details
            """

            def normalize_saved_action_results(saved_action_results):
                if not saved_action_results:
                    return

                saved_action_results['successful_entities'] = {
                    'length': get_chunks_length(self.enforcement_tasks_action_results_id_lists,
                                                saved_action_results['successful_entities']),
                    '_id': saved_action_results['successful_entities']
                }
                saved_action_results['unsuccessful_entities'] = {
                    'length': get_chunks_length(self.enforcement_tasks_action_results_id_lists,
                                                saved_action_results['unsuccessful_entities']),
                    '_id': saved_action_results['unsuccessful_entities']
                }

            def clear_saved_action_passwords(action):
                action_configs = self._get_actions_from_reports_plugin()
                if not action_configs:
                    return
                clear_passwords_fields(action['config'], action_configs[action['action_name']]['schema'])

            normalize_saved_action_results(task['result']['main']['action']['results'])
            clear_saved_action_passwords(task['result']['main']['action'])
            for key in [ACTIONS_SUCCESS_FIELD, ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD]:
                arr = task['result'][key]
                for x in arr:
                    normalize_saved_action_results(x['action']['results'])
                    clear_saved_action_passwords(x['action'])

            task_metadata = task.get('result', {}).get('metadata', {})
            return beautify_db_entry({
                '_id': task['_id'],
                'enforcement': task['post_json']['report_name'],
                'view': task_metadata['trigger']['view']['name'],
                'period': task_metadata['trigger']['period'],
                'condition': task_metadata['triggered_reason'],
                'started': task['started_at'],
                'finished': task['finished_at'],
                'result': task['result'],
                'task_name': get_task_full_name(task.get('post_json', {}).get('report_name', ''),
                                                task_metadata.get('pretty_id', ''))
            })

        return jsonify(beautify_task(self.enforcement_tasks_runs_collection.find_one({
            '_id': ObjectId(task_id)
        })))

    def beautify_task_entry(self, task):
        """
        Extract needed fields to build task as represented in the Frontend
        """
        success_rate = '0 / 0'
        status = 'In Progress'
        result = task.get('result', {})
        if not isinstance(result, dict):
            result = {}
        try:
            if task.get('job_completed_state') == StoredJobStateCompletion.Successful.name:
                main_results = result.get(ACTIONS_MAIN_FIELD, {}).get('action', {}).get('results', {})

                main_successful_count = get_chunks_length(self.enforcement_tasks_action_results_id_lists,
                                                          main_results.get('successful_entities', 0))

                main_unsuccessful_count = get_chunks_length(self.enforcement_tasks_action_results_id_lists,
                                                            main_results.get('unsuccessful_entities', 0))
                success_rate = f'{main_successful_count} / {main_successful_count + main_unsuccessful_count}'
                status = 'Completed'

            return beautify_db_entry({
                '_id': task.get('_id'),
                'result.metadata.success_rate': success_rate,
                'post_json.report_name':
                    get_task_full_name(task.get('post_json', {}).get('report_name', ''),
                                       result.get('metadata', {}).get('pretty_id', '')),
                'status': status,
                f'result.{ACTIONS_MAIN_FIELD}.name': result.get('main', {}).get('name', ''),
                'result.metadata.trigger.view.name': result.get('metadata', {}).get('trigger', {}).get('view', {}).get(
                    'name', ''),
                'started_at': task.get('started_at', ''),
                'finished_at': task.get('finished_at', '')
            })
        except Exception as e:
            logger.exception(f'Invalid task {task.get("_id")}')
            return beautify_db_entry({
                '_id': task.get('_id', 'Invalid ID'),
                'status': 'Invalid'
            })
