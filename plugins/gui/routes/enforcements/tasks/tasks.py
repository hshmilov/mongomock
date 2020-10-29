import logging

import pymongo
from bson import ObjectId
from flask import (jsonify)

from axonius.consts.report_consts import (ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD,
                                          ACTIONS_SUCCESS_FIELD,
                                          NOT_RAN_STATE, TRIGGER_RESULT_VIEW_NAME_FIELD,
                                          ACTION_NAME_FIELD, ACTION_FIELD, STARTED_AT_FIELD,
                                          TRIGGER_RESULT_PERIOD_FIELD)
from axonius.plugin_base import EntityType
from axonius.consts.report_consts import (ACTIONS_MAIN_FIELD)
from axonius.utils.gui_helpers import (paginated, filtered,
                                       sorted_endpoint, search_filter)
from axonius.mixins.triggerable import (StoredJobStateCompletion)
from axonius.utils.mongo_chunked import get_chunks_length
from gui.logic.db_helpers import beautify_db_entry
from gui.logic.entity_data import (get_task_full_name)
from gui.logic.login_helper import clear_passwords_fields
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in

# pylint: disable=no-member

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('tasks')
class Tasks:

    def _tasks_query(self, mongo_filter, enforcement_name=None, search_value=None):
        """
        General query for all Complete / In progress task that also answer given mongo_filter
        """
        if search_value:
            mongo_filter = {
                '$or': [
                    mongo_filter, {
                        'result.metadata.trigger.view.id': {
                            '$in': self.common.data.find_views_by_name_match(search_value)
                        }
                    }
                ]
            }

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
    @search_filter()
    @gui_route_logged_in()
    def enforcement_tasks(self, limit, skip, mongo_filter, mongo_sort, search):
        """
        path: /api/enforcements/tasks
        """
        if mongo_sort.get('status'):
            mongo_sort['job_completed_state'] = -1 * mongo_sort['status']
            del mongo_sort['status']

        tasks = self.enforcement_tasks_runs_collection.find(self._tasks_query(mongo_filter, search_value=search))
        if TRIGGER_RESULT_VIEW_NAME_FIELD in mongo_sort:
            beautiful_tasks = [self.beautify_task_entry(task) for task in tasks]
            sorted_tasks = sorted(beautiful_tasks, key=lambda e: e.get(TRIGGER_RESULT_VIEW_NAME_FIELD) or '',
                                  reverse=mongo_sort[TRIGGER_RESULT_VIEW_NAME_FIELD] == pymongo.DESCENDING)
            return jsonify(sorted_tasks[skip: (skip + limit)])
        sort = [(STARTED_AT_FIELD, pymongo.DESCENDING)] if not mongo_sort else list(mongo_sort.items())
        return jsonify([self.beautify_task_entry(x) for x in tasks.sort(sort).skip(skip).limit(limit)])

    @filtered()
    @gui_route_logged_in('count')
    def enforcement_tasks_count(self, mongo_filter):
        """
        Counts how many 'run' tasks are documented in the trigger history of reports plugin

        path: /api/enforcements/tasks/count
        """
        return jsonify(self.enforcement_tasks_runs_collection.count_documents(self._tasks_query(mongo_filter)))

    @gui_route_logged_in('<task_id>')
    def enforcement_task_by_id(self, task_id):
        """
        Fetch an entire 'run' record with all its results, according to given task_id

        path: /api/enforcements/tasks/<task_id>
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

            result = task.get('result')
            if not result:
                return {}

            if result.get(ACTIONS_MAIN_FIELD) and result[ACTIONS_MAIN_FIELD].get('action'):
                main_action = result[ACTIONS_MAIN_FIELD]['action']
                normalize_saved_action_results(main_action['results'])

                def clear_saved_action_passwords(action):
                    action_configs = self._get_actions_from_reports_plugin()
                    if not action_configs:
                        return
                    clear_passwords_fields(action['config'], action_configs[action['action_name']]['schema'])

                clear_saved_action_passwords(main_action)
                for key in [ACTIONS_SUCCESS_FIELD, ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD]:
                    arr = result.get(key, [])
                    for x in arr:
                        normalize_saved_action_results(x['action']['results'])
                        clear_saved_action_passwords(x['action'])

            task_metadata = result.get('metadata', {})
            trigger = task_metadata.get('trigger', {})
            trigger_view_name = ''
            trigger_view = trigger.get('view')
            if trigger_view:
                trigger_view_name = self.common.data.find_view_name(
                    EntityType(trigger_view['entity']), trigger_view['id'])
            return beautify_db_entry({
                '_id': task['_id'],
                'enforcement': task['post_json']['report_name'],
                'view': trigger_view_name,
                'period': trigger.get('period', ''),
                'condition': task_metadata.get('triggered_reason', ''),
                'started': task[STARTED_AT_FIELD],
                'finished': task['finished_at'],
                'result': result,
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

            trigger_view_name = ''
            task_metadata = result.get('metadata', {})
            trigger = task_metadata.get('trigger', {})
            if trigger:
                trigger_view = trigger['view']
                trigger_view_entity = EntityType(trigger_view['entity'])
                trigger_view_name = self.common.data.find_view_name(trigger_view_entity, trigger_view['id'])

            main_action = result.get(ACTIONS_MAIN_FIELD, {})
            main_action_type = main_action.get(ACTION_FIELD, {}).get(ACTION_NAME_FIELD)
            return beautify_db_entry({
                '_id': task.get('_id'),
                'result.metadata.success_rate': success_rate,
                'post_json.report_name':
                    get_task_full_name(task.get('post_json', {}).get('report_name', ''),
                                       result.get('metadata', {}).get('pretty_id', '')),
                'status': status,
                f'result.{ACTIONS_MAIN_FIELD}.name': main_action.get('name', ''),
                f'result.{ACTIONS_MAIN_FIELD}.type': main_action_type,
                TRIGGER_RESULT_VIEW_NAME_FIELD: trigger_view_name,
                TRIGGER_RESULT_PERIOD_FIELD: task_metadata.get('triggered_reason', ''),
                STARTED_AT_FIELD: task.get(STARTED_AT_FIELD, ''),
                'finished_at': task.get('finished_at', '')
            })
        except Exception:
            logger.exception(f'Invalid task {task.get("_id")}')
            return beautify_db_entry({
                '_id': task.get('_id', 'Invalid ID'),
                'status': 'Invalid'
            })
