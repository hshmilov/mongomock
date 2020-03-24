import datetime
import logging
import re
from collections import defaultdict
from threading import Lock
from typing import List

import cachetools
from bson.json_util import default
from frozendict import frozendict
from axonius.consts.gui_consts import SPECIFIC_DATA, ADAPTERS_DATA, \
    ADAPTERS_META, SPECIFIC_DATA_CONNECTION_LABEL, \
    SPECIFIC_DATA_CLIENT_USED, CORRELATION_REASONS, SPECIFIC_DATA_PLUGIN_UNIQUE_NAME
from axonius.consts.plugin_consts import PLUGIN_NAME, ADAPTERS_LIST_LENGTH
from axonius.utils.datetime import parse_date
from axonius.utils.mongo_chunked import read_chunked
import axonius.pql

logger = logging.getLogger(f'axonius.{__name__}')

METADATA_FIELDS_TO_PROJECT_FOR_GUI = ['client_used']
PREFERRED_SUFFIX = '_preferred'
ADAPTER_PROPERTIES_DB_ENTRY = 'adapters.data.adapter_properties'
ADAPTER_LAST_SEEN_DB_ENTRY = 'adapters.data.last_seen'


def convert_many_queries_to_elemmatch_helper(name: str, value: object, length_of_prefix: int):
    # This deals with the case where we're using the GUI to select only a subset of adapters
    # to query from whilst in specific_data
    # This case leads to a very complicated output from PQL that we have to carefully fix here
    if name == 'specific_data' and isinstance(value, dict) and len(value) == 1 and list(value)[0] == '$elemMatch':
        return value['$elemMatch']
    return {
        name[length_of_prefix:]: value
    }


def convert_many_queries_to_elemmatch(datas, prefix, include_outdated: bool):
    """
    Helper for fix_specific_data
    """
    length_of_prefix = len(prefix) + 1
    if len(datas) == 1:
        k, v = datas[0]

        _and = [
            convert_many_queries_to_elemmatch_helper(k, v, length_of_prefix)
        ]
    else:
        _and = [
            {
                '$or': [
                    convert_many_queries_to_elemmatch_helper(k, v, length_of_prefix)
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
            adapters_query_count = None
            # k will look like "adapters_data.markadapter.something"
            _, adapter_name, *field_path = k.split('.')
            field_path = 'data.' + '.'.join(field_path)
            if field_path == 'data.adapter_count':
                adapters_query = {'$exists': 1}
                adapters_query_count = process_adapter_count_filter(adapter_name, v)
                include_outdated = False
            else:
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
            if adapters_query_count is not None:
                elem_match.get('$or')[0] = {
                    'adapters': adapters_query,
                    '$where': adapters_query_count,
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
    prefix = 'specific_data'
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
        elif k == 'adapters' and isinstance(v, dict):
            operator = next(iter(v))
            if operator == '$in':
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
            elif isinstance(v[operator], dict) and next(iter(v[operator])) == '$size':
                find['$expr'] = {
                    operator: [
                        {
                            '$size': '$adapters'
                        }, v[operator]['$size']
                    ]
                }
                del find['adapters']
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


def parse_filter_uncached(filter_str: str, history_date=None) -> frozendict:
    """
    Translates a string representing of a filter to a valid MongoDB query for entities.
    This does a log of magic to support querying the regular DB

    :param filter_str:      The PQL filter to translate into Mongo query
    :param history_date:    The historical date requested, in order to calculate last X days
    :return:
    """

    if filter_str is None:
        return frozendict({})

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
    res = translate_filter_not(axonius.pql.find(filter_str)) if filter_str else {}
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
    return frozendict(res)


@cachetools.cached(cachetools.LRUCache(maxsize=100), lock=Lock())
def parse_filter_cached(filter_str: str, history_date=None) -> frozendict:
    """
    See parse_filter_uncached
    """
    return parse_filter_uncached(filter_str, history_date)


def translate_from_connection_labels(filter_str: str) -> str:

    # This prevents some looping imports
    from axonius.plugin_base import PluginBase

    query_connection_label_equal = f'({SPECIFIC_DATA_CONNECTION_LABEL} =='
    query_connection_label_exist = f'(({SPECIFIC_DATA_CONNECTION_LABEL} == ({{"$exists":true,"$ne":""}})))'
    query_connection_label_in = f'({SPECIFIC_DATA_CONNECTION_LABEL} in'

    def create_client_id_and_plugin_name_condition(client_id, plugin_unique_name) -> str:
        """

        Transform condition base 'specific_data.connection_label' to compound condition match build from:
         ('specific_data.client_used === <client_id> AND 'specific_data.plugin_unique_name == <plugin_unique_name>)

        :param client_id:  adapter client id
        :param plugin_unique_name: adapter unique name
        :return: transform filter string
        """

        return f'({SPECIFIC_DATA_CLIENT_USED} == "{client_id}" ' \
               f'and {SPECIFIC_DATA_PLUGIN_UNIQUE_NAME} == "{plugin_unique_name}" )'

    def create_or_separated_condition(label_conditions: list) -> str:
        """
        :param label_conditions:  list of formatted AQL connection label string ;
                            (specific_data.client_used == "http://10.0.2.149/_admin" and
                             specific_data.plugin_unique_name == "ansible_tower_adapter_0" )
        :return: filter str  ((A) or (B) or (C))
                 return null if list input is empty
        """
        if not label_conditions:
            return None
        return f'({" or ".join(label_conditions)})'

    def create_label_condition(label: str) -> str:
        """
        A Label can match multiple clients .
        client_info  = ( <client_id> , <plugin_unique_name> )

        :param label: a AQL adapter connection label
        :return: AQL filter string compatible
        """
        labels_info = [create_client_id_and_plugin_name_condition(client_id, name) for (client_id, name) in
                       client_labels.get(label, [])]
        if labels_info:
            return create_or_separated_condition(labels_info)
        return f'{SPECIFIC_DATA_CLIENT_USED} == []'

    client_labels = PluginBase.Instance.clients_labels()

    # transform operator exists with compound condition of all labels
    if query_connection_label_exist in filter_str:
        client_labels_ids = client_labels.values()
        client_details = [create_client_id_and_plugin_name_condition(client_id, name) for ids in client_labels_ids
                          for client_id, name in ids]
        all_connection_labels_condition = create_or_separated_condition(client_details)
        if all_connection_labels_condition:
            filter_str = filter_str.replace(query_connection_label_exist, all_connection_labels_condition)

    # transform operator 'in' with new compound condition per client in OR logic
    if query_connection_label_in in filter_str:
        matcher = re.search(f'{SPECIFIC_DATA_CONNECTION_LABEL}' + r' in \[(.+?)\]', filter_str)
        while matcher:
            filter_labels = matcher.group(1)
            labels_list = [label.strip('"') for label in filter_labels.split(',')]

            label_attributes = [create_label_condition(label) for label in labels_list]
            replace_str = create_or_separated_condition(label_attributes)
            filter_str = filter_str.replace(matcher.group(0), replace_str)

            # in case of complex conditions
            matcher = re.search(f'{SPECIFIC_DATA_CONNECTION_LABEL}' + r' in \[(.+?)\]', filter_str)

    # transform operator equal with compound condition to match (client_id,plugin_unique_name) tuple
    if query_connection_label_equal in filter_str:
        matcher = re.search(f'{SPECIFIC_DATA_CONNECTION_LABEL} == \"(.+?)\"', filter_str)
        while matcher:
            filter_str = filter_str.replace(matcher.group(0), create_label_condition(matcher.group(1)))
            matcher = re.search(f'{SPECIFIC_DATA_CONNECTION_LABEL} == \"(.+?)\"', filter_str)

    return filter_str


def parse_filter(filter_str: str, history_date=None) -> dict:
    """
    If given filter contains the keyword NOW, meaning it needs a calculation relative to current date,
    it must be recalculated, instead of using the cached result
    """
    if filter_str and SPECIFIC_DATA_CONNECTION_LABEL in filter_str:
        return dict(parse_filter_uncached(translate_from_connection_labels(filter_str), history_date))
    if filter_str and 'NOW' in filter_str:
        return dict(parse_filter_uncached(filter_str, history_date))
    return dict(parse_filter_cached(filter_str, history_date))


def process_adapter_count_filter(adapter_name, condition):
    if isinstance(condition, int):
        condition = f'count == {condition}'
    elif condition.get('$gt', None) is not None:
        condition = f'count > {condition.get("$gt")}'
    elif condition.get('$lt', None) is not None:
        condition = f'count < {condition.get("$lt")}'
    elif condition.get('$exists', None) is not None:
        condition = f'count > 0'
    elif condition.get('$in', None) is not None:
        condition = f'{str(condition.get("$in"))}.includes(count)'

    return f'''
            function() {{
                count = 0;
                this.adapters.forEach(adapter => {{
                    if (adapter.plugin_name == '{adapter_name}') count++;
                }});
                return {condition};
            }}'''


def process_filter(filter_str, history_date):
    # Handle predefined sequence representing a range of some time units from now back
    now = datetime.datetime.now() if not history_date else parse_date(history_date)

    def replace_now(match):
        return match.group().replace('NOW', f'AXON{int(now.timestamp())}')

    # Replace "NOW - ##" to "number - ##" so AQL can further process it
    filter_str = re.sub(r'(NOW)\s*[-+]\s*(\d+)([hdw])', replace_now, filter_str)

    matches = re.search(r'NOT\s*\[(.*)\]', filter_str)
    while matches:
        filter_str = filter_str.replace(matches.group(0), f'not ({matches.group(1)})')
        matches = re.search(r'NOT\s*\[(.*)\]', filter_str)

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


def extract_adapter_metadata(adapter: dict) -> dict:
    """
    extract metadata from adapter data dict, use predefined list of fields to project
    :param adapter: adapter data as dict
    :return: a dict representing the field and his value
    """
    return {current_field: adapter[current_field] for current_field
            in METADATA_FIELDS_TO_PROJECT_FOR_GUI if current_field in adapter}


# pylint: disable=R0912
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
    try:
        if entity is None:
            return None

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
        adapters_data = defaultdict(list)
        try:
            for adapter in specific_data:
                adapters_data[adapter[PLUGIN_NAME]].append(adapter.get('data'))
        except Exception:
            if ignore_errors:
                adapters_data = {}
            else:
                raise
        adapters_data = dict(adapters_data)

        adapters_meta = defaultdict(list)
        try:
            for adapter in specific_data:
                adapters_meta[adapter[PLUGIN_NAME]].append(extract_adapter_metadata(adapter))
        except Exception:
            if ignore_errors:
                adapters_meta = {}
            else:
                raise
        adapters_meta = dict(adapters_meta)

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
            ADAPTERS_META: adapters_meta,
            CORRELATION_REASONS: entity.get(CORRELATION_REASONS),
            'adapters': adapters,
            'labels': labels,
            'accurate_for_datetime': entity.get('accurate_for_datetime')
        }
    except Exception:
        logger.exception(f'Failed converting {entity}, when ignoring errors = {ignore_errors}')
        # This is a legit exception, still has to be raised.
        raise


def convert_db_projection_to_view(projection):
    if not projection:
        return None

    view_projection = {}
    for field, v in projection.items():
        splitted = field.split('.')

        if field in ['adapters', 'labels']:
            continue

        if splitted[0] == SPECIFIC_DATA:
            splitted[0] = 'adapters'
            if splitted[-1].endswith(PREFERRED_SUFFIX):
                if ADAPTER_PROPERTIES_DB_ENTRY not in view_projection:
                    view_projection[ADAPTER_PROPERTIES_DB_ENTRY] = 1
                if ADAPTER_LAST_SEEN_DB_ENTRY not in view_projection:
                    view_projection[ADAPTER_LAST_SEEN_DB_ENTRY] = 1
                save_last = splitted[-1]
                del splitted[-1]
                # pylint: disable=W0106
                [splitted.append(x) for x in save_last.replace(PREFERRED_SUFFIX, '').split('_')]
            view_projection['.'.join(splitted)] = v
            splitted[0] = 'tags'
            view_projection['.'.join(splitted)] = v
        elif splitted[0] == ADAPTERS_DATA:
            splitted[1] = 'data'
            splitted[0] = 'adapters'
            view_projection['.'.join(splitted)] = v
            splitted[0] = 'tags'
            view_projection['.'.join(splitted)] = v
        else:
            view_projection[field] = v
    return view_projection


def parse_filter_non_entities(filter_str: str, history_date=None):
    """
    Translates a string representing of a filter to a valid MongoDB query for anything but entities
    """
    if filter_str is None:
        return {}

    filter_str = filter_str.strip()
    filter_str = process_filter(filter_str, history_date)
    res = translate_filter_not(axonius.pql.find(filter_str)) if filter_str else {}
    return res
