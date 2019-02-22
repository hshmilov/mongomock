from typing import Iterable, List

from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

from axonius.plugin_base import PluginBase


@dataclass(frozen=True)
class TaskActionData(DataClassJsonMixin):
    action_name: str
    action_type: str
    success: bool
    additional_info: object


@dataclass(frozen=True)
class TaskData(DataClassJsonMixin):
    recipe_name: str
    recipe_pretty_id: int
    actions: List[TaskActionData]


def _get_all_actions_from_recipe(recipe_result):
    """
    Helper for get_all_task_data
    :param recipe_result: is the 'result' from the triggerable_history of reports
    :return: all the actions from the recipe
    """
    yield recipe_result['main']
    yield from recipe_result['success']
    yield from recipe_result['failure']
    yield from recipe_result['post']


def get_all_task_data(internal_axon_id: str) -> Iterable[TaskData]:
    """
    Gets all the recipes and actions that this entity has participated in
    :return: See TaskData
    """
    # Gets the ids of all the lists that this entity has participated in, and the respectful data for that entity
    # per list
    queried_groups = PluginBase.Instance.enforcement_tasks_action_results_id_lists.find({
        'chunk': {
            '$elemMatch': {
                'internal_axon_id': internal_axon_id
            }
        }
    }, projection={
        'chunk_group_id': 1,
        'chunk.$': 1
    })

    groups = {
        x['chunk_group_id']: x['chunk'][0]
        for x
        in queried_groups
    }

    in_group = {
        '$in': list(groups)
    }

    # Gets all recipes that have referenced the above groups
    recipes = PluginBase.Instance.enforcement_tasks_runs_collection.find({
        '$or': [
            # main
            {
                'result.main.action.results.successful_entities': in_group
            },
            {
                'result.main.action.results.unsuccessful_entities': in_group
            },
            # success
            {
                'result.success.action.results.successful_entities': in_group
            },
            {
                'result.success.action.results.unsuccessful_entities': in_group
            },
            # failure
            {
                'result.failure.action.results.unsuccessful_entities': in_group
            },
            {
                'result.failure.action.results.successful_entities': in_group
            },
            # post action
            {
                'result.post.action.results.successful_entities': in_group
            },
            {
                'result.post.action.results.unsuccessful_entities': in_group
            },
        ]
    })

    for recipe in recipes:
        result_data = recipe['result']
        actions = []
        for action in _get_all_actions_from_recipe(result_data):
            action_results = action['action']['results']

            relevant_group = groups.get(action_results['successful_entities'])
            if relevant_group:
                success = True
            else:
                relevant_group = groups.get(action_results['unsuccessful_entities'])
                if relevant_group:
                    success = False

            if relevant_group:
                action_run = TaskActionData(action['name'], action['action']['action_name'], success,
                                            relevant_group['status'])
                actions.append(action_run)

        data = TaskData(recipe['post_json']['report_name'], result_data['metadata']['pretty_id'], actions)
        yield data
