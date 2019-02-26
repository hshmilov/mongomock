import datetime
import json
import logging
import re

from typing import List
from bson.json_util import default
import pql

from axonius.consts.gui_consts import SPECIFIC_DATA, ADAPTERS_DATA
from axonius.consts.plugin_consts import PLUGIN_NAME, ADAPTERS_LIST_LENGTH
from axonius.utils.datetime import parse_date
from axonius.utils.mongo_chunked import read_chunked

logger = logging.getLogger(f'axonius.{__name__}')


def convert_many_queries_to_elemmatch(datas, prefix, include_outdated: bool):
    """
    Helper for fix_specific_data
    """
    if len(datas) == 1:
        k, v = datas[0]
        _and = [
            {k[len(prefix):]: v}
        ]
    else:
        _and = [
            {
                '$or': [
                    {
                        k[len(prefix):]: v
                    }
                    for k, v
                    in datas]
            }
        ]

    _and.append({
        'pending_delete': {
            '$ne': True
        }
    })
    if not include_outdated:
        _and.append({
            'data._old': {
                '$ne': True
            }
        })
    return {
        '$elemMatch': {
            '$and': _and
        }
    }


def convert_many_queries_to_elemmatch_for_adapters(datas, adapter_name, include_outdated: bool):
    """
    Helper for fix_adapter_data
    """
    _and = [
        {
            PLUGIN_NAME: adapter_name
        },
        {
            'pending_delete': {
                '$ne': True
            }
        }
    ]
    if len(datas) == 1:
        k, v = datas[0]
        _and.append({k: v})
    else:
        _and.append({
            '$or': [
                {
                    k: v
                }
                for k, v
                in datas
            ]
        })

    if not include_outdated:
        _and.append({
            'data._old': {
                '$ne': True
            }
        })
    return {
        '$elemMatch': {
            '$and': _and
        }
    }


def fix_adapter_data(find, include_outdated: bool):
    """
    Helper for post_process_add_old_filtering
    """
    prefix = 'adapters_data.'
    datas = [(k, v) for k, v in find.items() if k.startswith(prefix)]
    if datas:
        for k, v in datas:
            # k will look like "adapters_data.markadapter.something"
            _, adapter_name, *field_path = k.split('.')
            field_path = 'data.' + '.'.join(field_path)

            adapters_query = convert_many_queries_to_elemmatch_for_adapters([(field_path, v)], adapter_name,
                                                                            include_outdated)
            tags_query = convert_many_queries_to_elemmatch_for_adapters([(field_path, v)], adapter_name,
                                                                        include_outdated)
            tags_query['$elemMatch']['$and'].append({
                'type': 'adapterdata'
            })

            elem_match = {
                '$or': [
                    {
                        'adapters': adapters_query,
                    },
                    {
                        'tags': tags_query
                    }
                ]
            }
            find.update(elem_match)

        for k, _ in datas:
            del find[k]

    for k, v in find.items():
        if not k.startswith(prefix):
            post_process_filter(v, include_outdated)


def fix_specific_data(find, include_outdated: bool):
    """
    Helper for post_process_add_old_filtering
    """
    prefix = 'specific_data.'
    datas = [(k, v) for k, v in find.items() if k.startswith(prefix)]
    if datas:
        adapters_query = convert_many_queries_to_elemmatch(datas, prefix, include_outdated)
        tags_query = convert_many_queries_to_elemmatch(datas, prefix, include_outdated)
        tags_query['$elemMatch']['$and'].append({
            'type': 'adapterdata'
        })

        elem_match = {
            '$or': [
                {
                    'adapters': adapters_query,
                },
                {
                    'tags': tags_query
                }
            ]
        }

        find.update(elem_match)

    for k, _ in datas:
        del find[k]

    for k, v in find.items():
        if not k.startswith(prefix):
            post_process_filter(v, include_outdated)


def post_process_filter(find: dict, include_outdated: bool):
    """
    Post processing for the mongo filter:

    1. Fixes in place the mongo filter to not include 'old' entities - if include_outdated
    2. Fixes to translate all adapters_data to use specific_data instead

    """
    if isinstance(find, dict):
        fix_specific_data(find, include_outdated)
        fix_adapter_data(find, include_outdated)

    elif isinstance(find, list):
        for x in find:
            post_process_filter(x, include_outdated)


def convert_to_main_db(find):
    """
    Now that we dropped the view db, we have to hack this!
    Converts a query that was intended for the view into a query that works on the main DB
    """
    if isinstance(find, list):
        for x in find:
            convert_to_main_db(x)
        return

    if not isinstance(find, dict):
        raise Exception(f'not a dict! {find} ')

    if len(find) == 1:
        k = next(iter(find))
        v = find[k]
        if k.startswith('$'):
            convert_to_main_db(v)
        elif k == 'adapters' and isinstance(v, str):
            find['$or'] = [
                {
                    'adapters.plugin_name': v
                },
                {
                    'tags': {
                        '$elemMatch': {
                            '$and': [
                                {
                                    'plugin_name': v
                                },
                                {
                                    'type': 'adapterdata'
                                }
                            ]
                        }
                    }
                }
            ]
            del find[k]
        elif k == 'labels':
            find['tags.label_value'] = v
            del find[k]


INCLUDE_OUTDATED = 'INCLUDE OUTDATED: '
EXISTS_IN = 'exists_in('


def figure_out_axon_internal_id_from_query(recipe_run_pretty_id: str, condition: str,
                                           index_in_conditon: int, entities_returned_type: str) -> List[str]:
    """
    When querying, you can have a beginning that looks like this:
    exists_in(2, success, 0, successful_entities)

    :param recipe_run_pretty_id:    the pretty id of the recipe run instance,
                                    lookup reports_collection.triggerable_history under result.metadata.pretty_id
    :param condition:           the position -> condition of the saved action, look up the structure of a recipe
    :param index_in_conditon:   the position -> index of the saved action, each condition may have many actions
    :param entities_returned_type: either 'successful_entities' or 'unsuccessful_entities'
    :return: list of internal axon ids
    """
    # This prevents some looping imports
    from axonius.plugin_base import PluginBase

    specific_run = PluginBase.Instance.enforcement_tasks_runs_collection.find_one({
        'result.metadata.pretty_id': recipe_run_pretty_id
    })
    if not specific_run:
        return []
    result = specific_run['result']

    list_of_actions = result[condition]
    if condition == 'main':
        action = list_of_actions
    else:
        action = list_of_actions[index_in_conditon]
    if not action['action']['results']:
        return []
    return [x['internal_axon_id']
            for x
            in read_chunked(PluginBase.Instance.enforcement_tasks_action_results_id_lists,
                            action['action']['results'][entities_returned_type],
                            projection={
                                'chunk.internal_axon_id': 1
                            })]


def parse_filter(filter_str: str, history_date=None):
    """
    Translates a string representing of a filter to a valid MongoDB query for entities.
    This does a log of magic to support querying the regular DB
    """
    if filter_str is None:
        return {}

    include_outdated = False
    filter_str = filter_str.strip()
    if filter_str.startswith(INCLUDE_OUTDATED):
        include_outdated = True
        filter_str = filter_str[len(INCLUDE_OUTDATED):]

    filter_str = filter_str.strip()
    recipe_result_subset = None
    if filter_str.startswith(EXISTS_IN):
        filter_str = filter_str[len(EXISTS_IN):]
        recipe_id, condition, index_in_condition, entities_returned_type = (x.strip()
                                                                            for x
                                                                            in filter_str[:filter_str.index(')')].
                                                                            split(','))
        filter_str = filter_str[filter_str.index(')') + 1:].strip()

        recipe_result_subset = figure_out_axon_internal_id_from_query(int(recipe_id),
                                                                      condition,
                                                                      int(index_in_condition),
                                                                      entities_returned_type)
    filter_str = process_filter(filter_str, history_date)
    res = translate_filter_not(pql.find(filter_str)) if filter_str else {}
    post_process_filter(res, include_outdated)
    convert_to_main_db(res)
    res = {
        '$and': [res]
    }
    if recipe_result_subset is not None:
        res['$and'].append({
            'internal_axon_id': {
                '$in': recipe_result_subset
            }
        })
    return res


def process_filter(filter_str, history_date):
    # Handle predefined sequence representing a range of some time units from now back
    matches = re.search(r'NOW\s*-\s*(\d+)([hdw])', filter_str)
    while matches:
        computed_date = datetime.datetime.now() if not history_date else parse_date(history_date)
        # Create the start date intended
        if matches.group(2) == 'h':
            computed_date -= datetime.timedelta(hours=int(matches.group(1)))
        elif matches.group(2) == 'd':
            computed_date -= datetime.timedelta(days=int(matches.group(1)))
        elif matches.group(2) == 'w':
            computed_date -= datetime.timedelta(days=int(matches.group(1)) * 7)
        # Remove the predefined sequence
        filter_str = filter_str.replace(matches.group(0), computed_date.strftime('%m/%d/%Y %I:%M %p'))
        # Find next sequence
        matches = re.search(r'NOW\s*-\s*(\d+)([hdw])', filter_str)

    matches = re.search(r'NOT\s*\[(.*)\]', filter_str)
    while matches:
        filter_str = filter_str.replace(matches.group(0), f'not ({matches.group(1)})')
        matches = re.search(r'NOT\s*\[(.*)\]', filter_str)

    matches = re.findall(re.compile(r'match\s*\((\[.*?\])\)'), filter_str)
    for match in matches:
        filter_str = filter_str.replace(match, json.dumps(pql.find(match[1:-1]), default=default_iso_date))

    matches = re.findall(re.compile(r'({"\$date": (.*?)})'), filter_str)
    for match in matches:
        filter_str = filter_str.replace(match[0], f'date({match[1]})')

    return filter_str


def default_iso_date(obj):
    if isinstance(obj, datetime.datetime):
        return {'$date': obj.strftime('%m/%d/%Y %I:%M %p')}
    return default(obj)


def translate_filter_not(filter_obj):
    if isinstance(filter_obj, dict):
        translated_filter_obj = {}
        for key, value in filter_obj.items():
            if isinstance(value, dict) and '$not' in value:
                translated_filter_obj['$nor'] = [{key: translate_filter_not(value['$not'])}]
            else:
                translated_filter_obj[key] = translate_filter_not(value)
        return translated_filter_obj
    if isinstance(filter_obj, list):
        return [translate_filter_not(item) for item in filter_obj]
    return filter_obj


def convert_db_entity_to_view_entity(entity: dict, ignore_errors: bool = False) -> dict:
    """
    Following https://axonius.atlassian.net/browse/AX-2730 we have to have to changes

    Processing of entities into a "view" once in a while is expensive and problematic.

    However we're already grew accustomed to it, and habits are hard to break.

    So this method takes an entity as it is in the db and returns

    :param ignore_errors:   Sometimes you don't want to pass a full fledged object, i.e you want
                            to pass a very narrowly projected object. In this case, this pass TRUE here,
                            and the method will ignore as many missing fields as it can.
    """
    filtered_adapters = [adapter
                         for adapter in entity['adapters']
                         if adapter.get('pending_delete') is not True]

    try:
        labels = [tag['name']
                  for tag in entity['tags']
                  if tag['type'] == 'label' and tag['data'] is True]
    except Exception:
        if ignore_errors:
            labels = []
        else:
            raise

    specific_data = list(filtered_adapters)
    specific_data.extend(tag
                         for tag in entity['tags']
                         if (ignore_errors and 'type' not in tag) or tag['type'] == 'adapterdata')

    try:
        adapters_data = {
            adapter[PLUGIN_NAME]: adapter.get('data')
            for adapter
            in specific_data
        }
    except Exception:
        if ignore_errors:
            adapters_data = {}
        else:
            raise

    try:
        generic_data = [tag
                        for tag in entity['tags']
                        if tag['type'] == 'data' and tag['data'] is not False]
    except Exception:
        if ignore_errors:
            generic_data = []
        else:
            raise

    try:
        adapters = [adapter[PLUGIN_NAME]
                    for adapter
                    in filtered_adapters]
    except Exception:
        if ignore_errors:
            adapters = []
        else:
            raise

    return {
        '_id': entity.get('_id'),
        'internal_axon_id': entity.get('internal_axon_id'),
        ADAPTERS_LIST_LENGTH: entity.get(ADAPTERS_LIST_LENGTH),
        'generic_data': generic_data,
        SPECIFIC_DATA: specific_data,
        ADAPTERS_DATA: adapters_data,
        'adapters': adapters,
        'labels': labels,
        'accurate_for_datetime': entity.get('accurate_for_datetime')
    }


def parse_filter_non_entities(filter_str: str, history_date=None):
    """
    Translates a string representing of a filter to a valid MongoDB query for anything but entities
    """
    if filter_str is None:
        return {}

    filter_str = filter_str.strip()
    filter_str = process_filter(filter_str, history_date)
    res = translate_filter_not(pql.find(filter_str)) if filter_str else {}
    return res
