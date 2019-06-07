import datetime
import json
import logging
from itertools import chain
from multiprocessing.pool import ThreadPool
from typing import List, Iterable, Tuple

from enum import Enum
from bson import json_util
from bson.objectid import ObjectId
import pymongo
from pymongo.results import DeleteResult, UpdateResult
from flask import jsonify, request
from dataclasses import dataclass

from axonius.consts.plugin_subtype import PluginSubtype
from axonius.entities import EntityType
from axonius.mixins.triggerable import Triggerable, RunIdentifier
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.utils.axonius_query_language import parse_filter
from axonius.utils.files import get_local_config_file
from axonius.utils.mongo_escaping import unescape_dict
from axonius.consts.report_consts import (ACTIONS_FIELD, ACTIONS_MAIN_FIELD, ACTIONS_SUCCESS_FIELD,
                                          ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD, LAST_UPDATE_FIELD, TRIGGERS_FIELD,
                                          LAST_TRIGGERED_FIELD, TIMES_TRIGGERED_FIELD, NOT_RAN_STATE,
                                          CUSTOM_SELECTION_TRIGGER)
from axonius.types.enforcement_classes import (ActionInRecipe, Recipe, TriggerPeriod, Trigger, TriggerView,
                                               TriggerConditions, RunOnEntities, TriggeredReason, RecipeRunMetadata,
                                               ActionRunResults, DBActionRunResults, EntityResult, SavedActionType)
from axonius.utils.mongo_chunked import insert_chunked, read_chunked, create_indexes_on_collection

from reports.action_types.action_type_alert import ActionTypeAlert
from reports.action_types.action_type_base import ActionTypeBase
from reports.action_types.all_action_types import AllActionTypes

logger = logging.getLogger(f'axonius.{__name__}')


# See
# https://axonius.atlassian.net/wiki/spaces/AX/pages/793051137/New+Enforcement+center+Actions
# for the specs


@dataclass(frozen=True)
class QueryResultDiff:
    added: List[str]
    removed: List[str]


def query_result_diff(current_result: list, last_result: list) -> QueryResultDiff:
    """ get the current query result and last query result and create and returns
        a dict "diff_dict" that store the added entities and the removed entities """

    current_result = set(current_result)
    last_result = set(last_result or [])

    return QueryResultDiff(list(current_result - last_result), list(last_result - current_result))


# pylint: disable=E0213


class ReportsService(Triggerable, PluginBase):
    # The amount of internal_axon_ids that are saved in a single document in self.__internal_axon_ids_lists
    # Should be lower than document size, while not too low so pagination is common
    INTERNAL_AXON_IDS_PER_DOCUMENT = 100 * 1000

    def __init__(self, *args, **kwargs):
        """ This service is responsible for alerting users in several ways and cases when a
                        report query result changes. """

        super().__init__(get_local_config_file(__file__), *args, **kwargs)
        self.__reports_collection = self._get_collection('reports')
        self.__reports_collection.create_index([('name', pymongo.DESCENDING)], unique=True)
        self.__saved_actions_collection = self._get_collection('saved_actions')
        self.__saved_actions_collection.create_index([('name', pymongo.DESCENDING)], unique=True)

        # For the pretty id
        self.__running_id_collection = self._get_collection('running_id')
        self._get_collection('triggerable_history').create_index([('result.metadata.pretty_id', pymongo.DESCENDING)],
                                                                 unique=True,
                                                                 partialFilterExpression={
                                                                     'result.metadata.pretty_id': {
                                                                         '$exists': True
                                                                     }})

        # We can't save the lists of internal axon ids within our document, so we save those here
        # This is used for the report itself, i.e. to save state
        self.__internal_axon_ids_lists = self._get_collection('internal_axon_ids_lists')

        # We can't save the lists of internal axon ids within our document, so we save those here
        # This is used for the results of actions, the type here is EntitiesResult
        self.__action_results = self._get_collection('action_results')

        create_indexes_on_collection(self.__internal_axon_ids_lists)
        create_indexes_on_collection(self.__action_results)
        self.__action_results.create_index([('chunk.internal_axon_id', pymongo.ASCENDING)])

    def __save_entities_result(self, data: ActionRunResults) -> DBActionRunResults:
        """
        Like __insert_new_list_internal_axon_ids, but specifically for EntitiesResult
        """
        schema = EntityResult.schema()
        success = insert_chunked(self.__action_results, ReportsService.INTERNAL_AXON_IDS_PER_DOCUMENT,
                                 (schema.dump(x) for x in data.successful_entities))
        fail = insert_chunked(self.__action_results, ReportsService.INTERNAL_AXON_IDS_PER_DOCUMENT,
                              (schema.dump(x) for x in data.unsuccessful_entities))
        return DBActionRunResults(success, fail, data.exception_state or
                                  next(chain(data.successful_entities, data.unsuccessful_entities)).status)

    def __insert_new_list_internal_axon_ids(self, internal_axon_ids: List[str]) -> ObjectId:
        """
        Inserts the given list into the DB in a paginated form, and returns the _id
        """
        return insert_chunked(self.__internal_axon_ids_lists, ReportsService.INTERNAL_AXON_IDS_PER_DOCUMENT,
                              internal_axon_ids)

    def __get_internal_axon_ids(self, id_: ObjectId) -> Iterable[str]:
        """
        Gets an iterator for the list of internal axon ids from the internal_axon_ids_lists collection
        """
        return read_chunked(self.__internal_axon_ids_lists, id_)

    def __recipe_from_db(self, db_data, metadata: RecipeRunMetadata = None) -> Recipe:
        """
        DB Stores recipes in a slightly different way than in the Recipe dataclass
        Instead of having the actions, it stores their "name" (which is a unique key)
        """

        def get_action(name) -> ActionInRecipe:
            if not name:
                return name
            return ActionInRecipe.schema().make_actioninrecipe(self.__saved_actions_collection.find_one({
                'name': name
            }, projection={
                '_id': 0
            }))

        return Recipe(main=get_action(db_data[ACTIONS_MAIN_FIELD]),
                      success=[get_action(action) for action in db_data.get(ACTIONS_SUCCESS_FIELD) or []],
                      failure=[get_action(action) for action in db_data.get(ACTIONS_FAILURE_FIELD) or []],
                      post=[get_action(action) for action in db_data.get(ACTIONS_POST_FIELD) or []],
                      metadata=metadata
                      )

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name == 'execute':
            with ThreadPool(10) as pool:
                def run_specific_configuration(report_name, configuration_name):
                    self._trigger('run',
                                  priority=True,
                                  post_json={
                                      'report_name': report_name,
                                      'configuration_name': configuration_name
                                  })

                reports = self.__reports_collection.find(projection={
                    'name': 1,
                    f'{TRIGGERS_FIELD}.name': 1
                })
                to_run = ((sublist['name'], item['name'])
                          for sublist in reports
                          for item in sublist[TRIGGERS_FIELD])
                pool.starmap_async(run_specific_configuration, to_run).wait(timeout=36000)
            return ''

        if job_name == 'run':
            report = self.__reports_collection.find_one({
                'name': post_json['report_name']
            })
            if not report:
                raise LookupError('Can not find such a report')
            if post_json.get('configuration_name'):
                run_configuration = [x for x in report[TRIGGERS_FIELD]
                                     if x['name'] == post_json['configuration_name']]
                if not len(run_configuration) == 1:
                    raise LookupError(f'Found {len(run_configuration)} instances of the given configuration')
                result = self.__process_run_configuration(report, Trigger.from_dict(run_configuration[0]),
                                                          run_identifier, post_json.get('manual', False))
            elif post_json.get('input'):
                result = self.__process_run_configuration(report, Trigger(
                    name=post_json['report_name'],
                    view=TriggerView(name=CUSTOM_SELECTION_TRIGGER, entity=EntityType[post_json['input']['entity']]),
                    conditions=TriggerConditions(new_entities=False, previous_entities=False, above=-1, below=-1),
                    period=TriggerPeriod.never,
                    last_triggered=None,
                    result=None,
                    result_count=0,
                    times_triggered=0,
                    run_on=RunOnEntities.AllEntities
                ), run_identifier, manual=True, manual_input=post_json['input'])
            else:
                result = None
            if not result:
                return NOT_RAN_STATE

            result = json.loads(result.to_json(default=self.__default_for_trigger), object_hook=json_util.object_hook)
            return result

        raise NotImplementedError('No such job')

    @add_rule('reports/<report_id>/<trigger_name>', methods=['POST', 'DELETE'])
    def edit_trigger_by_id(self, report_id: str, trigger_name: str):
        """
        Modify some report trigger
        POST   - update or create
        DELETE - delete
        :param report_id: the report _id
        :param trigger_name: the name of the trigger to change, create or update
        """
        if request.method == 'POST':
            processed_trigger = self.__process_trigger(self.get_request_data_as_object())
            processed_trigger.pop(LAST_TRIGGERED_FIELD, None)

            with self.__reports_collection.start_session() as session:
                with session.start_transaction():
                    result = session.update_one({
                        '_id': ObjectId(report_id),
                        'triggers.name': trigger_name
                    }, {
                        '$set': {
                            f'triggers.$.{k}': v
                            for k, v
                            in processed_trigger.items()
                        }
                    })
                    if result.matched_count == 0:
                        # this means the update failed, now we need to push it
                        logger.info(f'Failed to update trigger {trigger_name} - adding it to list')
                        session.update_one({
                            '_id': ObjectId(report_id),
                        }, {
                            '$push': {
                                'triggers': processed_trigger
                            }
                        })
        elif request.method == 'DELETE':
            self.__reports_collection.update_one({
                '_id': ObjectId(report_id),
            }, {
                '$pull': {
                    'triggers': {
                        'name': trigger_name
                    }
                }
            })
        return ''

    @add_rule('reports/<report_id>', methods=['POST'])
    def report_by_id(self, report_id: str):
        """
        Update a specific report's recipe
        """
        report_data = self.get_request_data_as_object()
        result = self.__reports_collection.update_one({
            '_id': ObjectId(report_id),
        }, {
            '$set': {
                ACTIONS_FIELD: report_data[ACTIONS_FIELD],
                LAST_UPDATE_FIELD: datetime.datetime.utcnow()
            }
        })
        return jsonify({'modified': result.modified_count})

    @add_rule('reports', methods=['PUT', 'DELETE'])
    def report(self):
        """The Rest reports endpoint.

        Creates and deletes the reports resources.
        """
        try:
            if self.get_method() == 'PUT':
                return self._add_report(self.get_request_data_as_object())

            # Assumed DELETE
            return jsonify({'deleted': self._remove_report(self.get_request_data_as_object()).deleted_count})
        except ValueError:
            message = 'Expected JSON, got something else...'
            logger.exception(message)
            return return_error(message, 400)

    @staticmethod
    def __default_for_trigger(obj):
        if isinstance(obj, TriggerPeriod):
            return obj.name
        if isinstance(obj, Enum):
            return obj.value
        return json_util.default(obj)

    def __process_trigger(self, trigger):
        trigger_obj = Trigger.from_dict(trigger)
        view_result = self.get_view_results(trigger_obj.view.name, trigger_obj.view.entity)
        trigger_obj.result = self.__insert_new_list_internal_axon_ids(view_result)
        trigger_obj.result_count = len(view_result)
        return json.loads(trigger_obj.to_json(default=self.__default_for_trigger), object_hook=json_util.object_hook)

    def __processed_triggers(self, triggers: List[dict]) -> Iterable[Trigger]:
        """
        Create internal Trigger types from given GUI triggers
        """
        for trigger in triggers:
            yield self.__process_trigger(trigger)

    def _add_report(self, report_data):
        """Adds a reports on a query.

        Creates a reports resource which is a query on our device_db that the user or a plugin wants to be notified when
        it's result changes (criteria should indicate whether to notify in
        only a specific change to the results or any).
        :param dict report_data: The query to reports (as a valid mongo query) and criteria.
        :return: Correct HTTP response.
        """
        # Checks if requested query isn't already watched.
        try:
            report_resource = {
                LAST_UPDATE_FIELD: datetime.datetime.utcnow(),
                ACTIONS_FIELD: report_data['actions'],
                'name': report_data['name'],
                TRIGGERS_FIELD: list(self.__processed_triggers(report_data[TRIGGERS_FIELD])),
                'user_id': ObjectId(report_data['user_id'])
            }

            # Pushes the resource to the db.
            insert_result = self.__reports_collection.insert_one(report_resource)
            logger.info('Added query to reports list')

            return str(insert_result.inserted_id), 201
        except ValueError as e:
            message = str(e)
            logger.exception(message)
            return return_error(message, 400)
        except KeyError as e:
            message = 'The query reports request is missing data. Details: {0}'.format(str(e))
            logger.exception(message)
            return return_error(message, 400)

    def _remove_report(self, reports_ids: Iterable[str]) -> DeleteResult:
        """
        Deletes reports from the DB using their _id
        """
        report_ids = [ObjectId(report_id) for report_id in reports_ids]
        report_ids_query = {
            '_id': {
                '$in': report_ids
            }
        }
        all_actions = [
            [x[ACTIONS_MAIN_FIELD]] + x[ACTIONS_SUCCESS_FIELD] + x[ACTIONS_FAILURE_FIELD] + x[ACTIONS_POST_FIELD]
            for x
            in [report['actions'] for report in self.__reports_collection.find(report_ids_query, {'actions': 1})]
        ]
        self.__saved_actions_collection.delete_many({
            'name': {
                '$in': [action for sub_actions in all_actions for action in sub_actions]
            }
        })
        return self.__reports_collection.delete_many(report_ids_query)

    def __get_pretty_id(self) -> int:
        """
        Returns an increasing id for nice IDs in triggerable history
        """
        return self.__running_id_collection.find_one_and_update(
            filter={},
            update={'$inc': {'number': 1}},
            upsert=True,
            return_document=pymongo.ReturnDocument.AFTER
        )['number']

    @add_rule('reports/actions', methods=['GET'])
    # pylint: disable=no-self-use
    def actions(self):
        """
        All action names and their schema, as defined by the author of the class
        """
        return jsonify({
            action_name: {
                'schema': action_class.config_schema(),
                'default': action_class.default_config()
            }
            for action_name, action_class in AllActionTypes.items()})

    def get_view_results(self, view_name: str, view_entity: EntityType) -> List:
        """
        Gets a query's results from the DB.

        :param view_name: The query name.
        :param view_entity: The query entity type name.
        :return: The results of the query.
        """
        projection = {
            'internal_axon_id': 1
        }

        query = self.gui_dbs.entity_query_views_db_map[view_entity].find_one({'name': view_name})
        if query is None:
            raise ValueError(f'Missing query "{view_name}"')
        parsed_query_filter = parse_filter(query['view']['query']['filter'])

        # Projection to get only the needed data to differentiate between results.
        return [x['internal_axon_id']
                for x
                in self._entity_db_map[view_entity].find(parsed_query_filter, projection)]

    @staticmethod
    def _get_triggered_reports(current_result, diff_dict: QueryResultDiff,
                               conditions: TriggerConditions) -> List[TriggeredReason]:
        """
        get the actual set of reports that was triggered this cycle

        :param diff_dict: dict that represent the changes between last cycle and this one.
        :param conditions: the user defined conditions for trigger
        :return: A set of triggered trigger reasons.
        """
        if (not conditions.new_entities and not conditions.previous_entities
                and conditions.above is None and conditions.below is None):
            return [TriggeredReason.every_discovery]

        triggered = set()

        # If there was change
        if conditions.new_entities and diff_dict.added:
            triggered.add(TriggeredReason.new_entities)

        if conditions.previous_entities and diff_dict.removed:
            triggered.add(TriggeredReason.previous_entities)

        if conditions.above is not None and len(current_result) > int(conditions.above) and int(conditions.above) > 0:
            triggered.add(TriggeredReason.above)

        if conditions.below is not None and len(current_result) < int(conditions.below):
            triggered.add(TriggeredReason.below)

        return list(triggered)

    def _call_actions(self,
                      report_data, recipe: Recipe,
                      triggered: List[TriggeredReason],
                      trigger: Trigger,
                      current_result: List[str],
                      added_results: List[str],
                      removed_results: List[str]) -> Recipe:
        """
        Calls the actions in the recipe of the given report
        :param report_data: The report, as is, in the DB
        :param recipe: The parsed recipe from the report
        :param triggered: The set of reasons for this specific trigger to be triggered
        :param trigger: The specific trigger that this should apply for
        :param current_result: The list of entities (internal axon ids) to perform on
        :return: A recipe with all the results in it as well
        """

        def get_action_from_recipe_action(recipe_action: ActionInRecipe,
                                          internal_axon_ids: List[str]) -> ActionTypeBase:
            action_class = AllActionTypes[recipe_action.action.action_name]
            if issubclass(action_class, ActionTypeAlert):
                return action_class(action_saved_name=recipe_action.name,
                                    config=recipe_action.action.config,
                                    run_configuration=trigger,
                                    report_data=report_data,
                                    triggered_set=triggered,
                                    internal_axon_ids=list(current_result),
                                    entity_type=trigger.view.entity,
                                    added_axon_ids=list(added_results),
                                    removed_axon_ids=list(removed_results))
            if issubclass(action_class, ActionTypeBase):
                return action_class(action_saved_name=recipe_action.name,
                                    config=recipe_action.action.config,
                                    run_configuration=trigger,
                                    report_data=report_data,
                                    triggered_set=triggered,
                                    internal_axon_ids=list(internal_axon_ids),
                                    entity_type=trigger.view.entity)
            raise RuntimeError('No such action')

        if not recipe.main:
            return recipe

        main_action = get_action_from_recipe_action(recipe.main,
                                                    list(current_result))

        recipe.main.action.results = main_action.run()
        recipe.main.action.action_type = SavedActionType.alert.name if isinstance(main_action, ActionTypeAlert) \
            else SavedActionType.action.name

        def get_all_actions() -> Iterable[Tuple[ActionInRecipe, ActionTypeBase]]:
            """
            Gets, in iterable form, all the actions in the recipe (except the main action)
            and the built ActionTypeBase for them. The ActionTypeBase will already have the appropriate
            entities in it (according to the recipe: either those that succeed, failed or all of them)
            """
            main_result = recipe.main.action.results
            successful_entities = [x.internal_axon_id
                                   for x
                                   in main_result.successful_entities]
            unsuccessful_entities = [x.internal_axon_id
                                     for x
                                     in main_result.unsuccessful_entities]
            recipe.main.action.results = self.__save_entities_result(main_result)

            successful_count = len(successful_entities)
            unsuccessful_count = len(unsuccessful_entities)
            if successful_count or unsuccessful_count:
                recipe.metadata.success_rate = successful_count / (successful_count + unsuccessful_count)

            for on_success in recipe.success:
                yield on_success, get_action_from_recipe_action(on_success, successful_entities)

            for on_fail in recipe.failure:
                yield on_fail, get_action_from_recipe_action(on_fail, unsuccessful_entities)

            for on_always in recipe.post:
                yield on_always, get_action_from_recipe_action(on_always, current_result)

        with ThreadPool(10) as pool:
            def _run(recipe_action: ActionInRecipe, action: ActionTypeBase):
                """
                Runs the action and saves the result into the recipe_action for saving
                """
                if not action:
                    return
                recipe_action.action.action_type = SavedActionType.alert.name if isinstance(action, ActionTypeAlert) \
                    else SavedActionType.action.name
                recipe_action.action.results = self.__save_entities_result(action.run())

            pool.starmap_async(_run, get_all_actions()).wait(timeout=3600)

        return recipe

    def __update_run_configuration(self, report_id: ObjectId, run_configuration_name: str,
                                   update_query) -> UpdateResult:
        """
        Updates a run configuration that is a part of a report
        :param report_id: the report it is part of
        :param run_configuration_name: the name of the configuration query
        :param update_query: the mongo update query
        :return:
        """
        return self.__reports_collection.update_one({
            '_id': report_id
        }, update=update_query, array_filters=[{
            'i.name': run_configuration_name
        }])

    def __process_run_configuration(self, report, trigger: Trigger, run_id: RunIdentifier, manual: bool = False,
                                    manual_input: dict = None) -> Recipe:
        """
        Processes a run configuration:
        Figures out if it is supposed to run;
        If so,
            runs the recipe upon it;
            Updates metadata and last results
        :param report: the relevant report with the recipe
        :param trigger: the specific run configuration to use
        :param run_id: the associated run id
        :param manual: the specific run was triggered manually, so no need to check period or conditions
        :param manual_input: A custom selection of entities to run on, instead of Trigger's query results
        :return: Updated Recipe in case the configuration has run
        """
        result = None
        if trigger.period == TriggerPeriod.never and not manual:
            return result

        if trigger.last_triggered and trigger.period != TriggerPeriod.all and not manual:
            now = datetime.datetime.utcnow()
            if trigger.period == TriggerPeriod.daily:
                max_date = now - datetime.timedelta(days=1)
            if trigger.period == TriggerPeriod.weekly:
                max_date = now - datetime.timedelta(days=7)
            if trigger.period == TriggerPeriod.monthly:
                max_date = now - datetime.timedelta(days=31)
            if trigger.last_triggered > max_date:
                return result

        if manual_input:
            query_result = self.get_selected_entities(
                EntityType[manual_input['entity']], manual_input['selection'], unescape_dict(manual_input['filter']))
        else:
            query_result = self.get_view_results(trigger.view.name, trigger.view.entity)

        query_difference = query_result_diff(query_result, self.__get_internal_axon_ids(trigger.result))
        triggered_reason = self._get_triggered_reports(query_result, query_difference,
                                                       trigger.conditions) if not manual else [TriggeredReason.manual]

        if not triggered_reason and trigger.result is None:
            # this means that this is the first run for a query that has specific conditions,
            # it is vital to update the run_configuration.result for future triggers
            id_ = self.__insert_new_list_internal_axon_ids(query_result)
            self.__update_run_configuration(report['_id'], trigger.name,
                                            {
                                                '$set': {
                                                    f'{TRIGGERS_FIELD}.$[i].result': id_,
                                                    f'{TRIGGERS_FIELD}.$[i].result_count': len(query_result)
                                                }})

        logger.debug(f'Triggered with {triggered_reason} '
                     f'query_difference = {query_difference} '
                     f'current_query_result = {query_result} ')

        if triggered_reason:
            reasons = [reason.value.format(getattr(trigger.conditions, reason.name, '')) for reason in triggered_reason]
            recipe = self.__recipe_from_db(report['actions'], RecipeRunMetadata(trigger, reasons, 0))
            recipe.metadata.pretty_id = self.__get_pretty_id()
            run_id.update_status(json.loads(recipe.to_json(
                default=self.__default_for_trigger), object_hook=json_util.object_hook))

            result = self._call_actions(report, recipe, triggered_reason, trigger,
                                        query_difference.added
                                        if trigger.run_on == RunOnEntities.AddedEntities
                                        else query_result,
                                        query_difference.added, query_difference.removed)

            # Update last triggered.
            self.__update_run_configuration(report['_id'], trigger.name, {
                '$set': {
                    f'{TRIGGERS_FIELD}.$[i].result': self.__insert_new_list_internal_axon_ids(query_result),
                    f'{TRIGGERS_FIELD}.$[i].result_count': len(query_result),
                    f'{TRIGGERS_FIELD}.$[i].{LAST_TRIGGERED_FIELD}': datetime.datetime.utcnow()
                },
                '$inc': {
                    f'{TRIGGERS_FIELD}.$[i].{TIMES_TRIGGERED_FIELD}': 1
                }
            })
        return result

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.PostCorrelation
