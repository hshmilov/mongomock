import datetime
import logging
import re
from collections import defaultdict
from threading import Lock
from typing import List

import cachetools
from bson import ObjectId
from bson.json_util import default
from frozendict import frozendict

from axonius.consts.gui_consts import SPECIFIC_DATA, ADAPTERS_DATA, \
    ADAPTERS_META, CLIENT_USED, PLUGIN_UNIQUE_NAME, \
    SPECIFIC_DATA_CLIENT_USED, CORRELATION_REASONS, HAS_NOTES, SPECIFIC_DATA_PLUGIN_UNIQUE_NAME,\
    SAVED_QUERY_PLACEHOLDER_REGEX, OS_DISTRIBUTION_GT_LT_QUERY_REGEX
from axonius.consts.plugin_consts import PLUGIN_NAME, ADAPTERS_LIST_LENGTH
from axonius.consts.system_consts import MULTI_COMPARE_MAGIC_STRING, COMPARE_MAGIC_STRING
from axonius.utils.datetime import parse_date
from axonius.utils.mongo_chunked import read_chunked
from axonius.devices.msft_versions import ENUM_WINDOWS_VERSIONS
import axonius.pql

logger = logging.getLogger(f'axonius.{__name__}')

METADATA_FIELDS_TO_PROJECT_FOR_GUI = ['client_used']
PREFERRED_SUFFIX = '_preferred'
PREFERRED_FIELDS = 'preferred_fields'
ADAPTER_PROPERTIES_DB_ENTRY = 'adapters.data.adapter_properties'
ADAPTER_LAST_SEEN_DB_ENTRY = 'adapters.data.last_seen'
OS_DISTRIBUTION_GT_SUFFIX = 'os.distribution >'
OS_DISTRIBUTION_LT_SUFFIX = 'os.distribution <'


def convert_many_queries_to_elemmatch_helper(name: str, value: object, length_of_prefix: int):
    # This deals with the case where we're using the GUI to select only a subset of adapters
    # to query from whilst in specific_data
    # This case leads to a very complicated output from PQL that we have to carefully fix here
    if name == 'specific_data' and isinstance(value, dict) and len(value) == 1 and list(value)[0] == '$elemMatch':
        return value['$elemMatch']
    return {
        name[length_of_prefix:]: value
    }


def convert_many_queries_to_elemmatch(datas, prefix, include_outdated: bool, preferred=False):
    """
    Helper for fix_specific_data
    """
    length_of_prefix = len(prefix) + 1
    if preferred:
        _and = []
        for data in datas:
            k, v = data
            _and.append({k.replace('specific_data.data', PREFERRED_FIELDS): v})
        return _and
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
        preferred_fields_query = []
        if any(x[0].endswith(PREFERRED_SUFFIX) for x in datas):
            preferred_fields_query = convert_many_queries_to_elemmatch(datas, PREFERRED_SUFFIX, include_outdated,
                                                                       preferred=True)
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
                },
            ]
        }
        if preferred_fields_query:
            elem_match['$or'].append(*preferred_fields_query)
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
    res = replace_data_in_query(COMPARE_MAGIC_STRING, process_compare_query, res)
    res = replace_data_in_query(MULTI_COMPARE_MAGIC_STRING, process_multi_compare_query, res)

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


# pylint: disable=R1710,R0912
def replace_data_in_query(magic: str, replace_function: callable, query: dict) -> dict:
    """
    This function receives a query, check whether `magic` is in the received query dict.
    It does that by running through the whole dict recursively (only by the types that can actually appear in this dict)
    if it finds the desired magic string, it passes it on to `replace_function` to process the special query,
    update the result from `process_compare_query` and return the new process query to the system.
    :param magic: a magic string to search in the dict
    :param replace_function: a callable function to handle the part of the dict that needs to be replaced
    :param query: a dictionary with the query the user entered
    :return: a processed query that can handle regular field comparison queries in the mongoDB
    """
    if magic in query:
        return replace_function(query[magic])
    if isinstance(query, list):
        for i, list_value in enumerate(query):
            if isinstance(list_value, (list, dict)) and magic in list_value:
                query[i] = replace_function(list_value[magic])
            elif isinstance(list_value, (list, dict)):
                query[i] = replace_data_in_query(magic, replace_function, list_value)
    elif isinstance(query, dict):
        for k, v in query.items():
            if isinstance(v, dict):
                query[k] = replace_data_in_query(magic, replace_function, v)
            if isinstance(v, list):
                for i, list_value in enumerate(v):
                    if isinstance(list_value, (list, dict)) and magic in list_value:
                        v[i] = replace_function(list_value[magic])
                    elif isinstance(list_value, (list, dict)):
                        v[i] = replace_data_in_query(magic, replace_function, list_value)
            if k == magic:
                query.update(replace_function(v))
                del k
        return query


def process_multi_compare_query(compare_statement: dict) -> dict:
    """
    This function gets a dict that represent a complex field comparison query.
    The dict should look like the following:
    {
        Operator (<,>,==): Days_Addition_or_Decline_number,
        Sub_Operator (+,-): [
            first_field_full_name,
            second_field_full_name
        ]
    }
    Which can be translated to that query (for better understanding):
    first_field_full_name + 1 < second_field_full_name
    first_field_full_name > second_field_full_name + 1
    Just like in reverse polish notation
    The function analyze each component of the query and put it in a JS filter query to be used by the mongoDB.
    :param compare_statement: A part of the whole query which needs to be handled
    :return: the replacement of the received statement that mongoDB can handle
    """
    if 'Gt' in compare_statement:
        main_operator = '>'
        check_number = compare_statement['Gt']
        del compare_statement['Gt']
    elif 'Lt' in compare_statement:
        main_operator = '<'
        check_number = compare_statement['Lt']
        del compare_statement['Lt']
    if 'Add' in compare_statement:
        sub_operator = '+'
    elif 'Sub' in compare_statement:
        sub_operator = '-'
    # Extracting the two fields from the received dict
    first_field, second_field = [(compare_statement[stmt][0], compare_statement[stmt][1])
                                 for stmt in compare_statement][0]
    # Extract the adapter name field path from the full field name
    # For example adapters_data.esx_adapter.os.distribution
    #                  ^            ^          ^
    #              Redundant     Adapter Name  Field Path
    #                 ()         (esx_adapter) ['os', 'distribution']
    _, first_adapter_name, *first_field_path = first_field.split('.')
    _, second_adapter_name, *second_field_path = second_field.split('.')
    # Joining the field path from list to string again
    first_field_path = '.'.join(first_field_path)
    second_field_path = '.'.join(second_field_path)
    return {
        '$where': f'''
        function() {{
            firstValue = "";
            secondValue = "";
            this.adapters.forEach(adapter => {{
                if (adapter.plugin_name == '{first_adapter_name}') {{
                    if ("{first_field_path}".split('.').length > 1) {{
                        tmpVal = adapter.data;
                        "{first_field_path}".split('.').forEach(key => {{
                            if (firstValue === "" && tmpVal[key] !== undefined) tmpVal = tmpVal[key];
                            else {{
                                firstValue = false;
                            }}
                        }})
                    }}
                    else if (adapter.data.{first_field_path} !== undefined && typeof(adapter.data.{first_field_path}.getDay) == "function") {{
                        firstValue = adapter.data.{first_field_path};
                    }}
                }}
                if (adapter.plugin_name == '{second_adapter_name}') {{
                    if ("{second_field_path}".split('.').length > 1) {{
                        tmpVal = adapter.data;
                        "{second_field_path}".split('.').forEach(key => {{
                            if (secondValue === "" && tmpVal[key] !== undefined) tmpVal = tmpVal[key];
                            else {{
                                secondValue = false;
                            }}
                        }})
                    }}
                    else if (adapter.data.{second_field_path} !== undefined && typeof(adapter.data.{second_field_path}.getDay) == "function") {{
                        secondValue = adapter.data.{second_field_path};
                    }}
                }}
            }})
            if (!firstValue || !secondValue) return false;
            firstValue.setHours(0,0,0,0);
            secondValue.setHours(0,0,0,0);
            if ("{main_operator}" == ">") {{
                return firstValue.getTime() {main_operator} secondValue.setDate(secondValue.getDate() {sub_operator} {check_number});
            }}
            return firstValue.setDate(firstValue.getDate() {sub_operator} {check_number}) {main_operator} secondValue.getTime();
        }}
        '''
    }


def process_compare_query(compare_statement: dict) -> dict:
    """
    This function gets a dict that represent a regular field comparison query.
    The dict should look like the following:
    {
        Operator (<,>,==): [
            first_field_full_name,
            second_field_full_name
        ]
    }
    Which can be translated to that query (for better understanding): first_field_full_name > second_field_full_name
    Just like in reverse polish notation
    The function analyze each component of the query and put it in a JS filter query to be used by the mongoDB.
    :param compare_statement: A part of the whole query which needs to be handled
    :return: the replacement of the received statement that mongoDB can handle
    """
    # Translating the main operator
    if 'Eq' in compare_statement:
        operator = '=='
    elif 'Gt' in compare_statement:
        operator = '>'
    elif 'Lt' in compare_statement:
        operator = '<'
    elif 'NotEq' in compare_statement:
        operator = '!='
    elif 'GtE' in compare_statement:
        operator = '>='
    elif 'LtE' in compare_statement:
        operator = '<='
    # Extracting the two fields from the received dict
    first_field, second_field = [(compare_statement[stmt][0], compare_statement[stmt][1])
                                 for stmt in compare_statement][0]
    # Extract the adapter name field path from the full field name
    # For example adapters_data.esx_adapter.os.distribution
    #                  ^            ^          ^
    #              Redundant     Adapter Name  Field Path
    #                 ()         (esx_adapter) ['os', 'distribution']
    _, first_adapter_name, *first_field_path = first_field.split('.')
    _, second_adapter_name, *second_field_path = second_field.split('.')
    # Joining the field path from list to string again
    first_field_path = '.'.join(first_field_path)
    second_field_path = '.'.join(second_field_path)
    return {
        '$where': f'''
        function() {{
            firstValue = "";
            secondValue = "";
            this.adapters.forEach(adapter => {{
                if (adapter.plugin_name == '{first_adapter_name}') {{
                    if ("{first_field_path}".split('.').length > 1) {{
                        tmpVal = adapter.data;
                        "{first_field_path}".split('.').forEach(key => {{
                            if (firstValue === "" && tmpVal[key] !== undefined) tmpVal = tmpVal[key];
                            else {{
                                firstValue = null;
                            }}
                        }})
                    }}
                    if (firstValue === "" && adapter.data.{first_field_path} !== undefined && typeof(adapter.data.{first_field_path}.getDay) == 'function') {{
                        firstValue = adapter.data.{first_field_path};
                        firstValue.setHours(0,0,0,0);
                        firstValue = firstValue.getTime()
                    }}
                    else if (firstValue === "" && adapter.data.{first_field_path} !== undefined) {{
                        firstValue = adapter.data.{first_field_path};
                    }}
                }}
                if (adapter.plugin_name == '{second_adapter_name}') {{
                    if ("{second_field_path}".split('.').length > 1) {{
                        tmpVal = adapter.data;
                        "{second_field_path}".split('.').forEach(key => {{
                            if (secondValue === "" && tmpVal[key] !== undefined) tmpVal = tmpVal[key];
                            else {{
                                secondValue = null;
                            }}
                        }})
                    }}
                    if (secondValue === "" && adapter.data.{second_field_path} !== undefined && typeof(adapter.data.{second_field_path}.getDay) == 'function') {{
                        secondValue = adapter.data.{second_field_path};
                        secondValue.setHours(0,0,0,0);
                        secondValue = secondValue.getTime()
                    }}
                    else if (secondValue === "" && adapter.data.{second_field_path} !== undefined) {{
                        secondValue = adapter.data.{second_field_path};
                    }}
                }}
            }})
            if (firstValue == null || secondValue == null) {{
                return false;
            }}
            if (typeof(firstValue) === "boolean" && typeof(secondValue) === "boolean") {{
                return firstValue == secondValue;
            }}
            if (!firstValue || !secondValue) return false;
            return firstValue {operator} secondValue;
        }}
        '''
    }


@cachetools.cached(cachetools.LRUCache(maxsize=100), lock=Lock())
def parse_filter_cached(filter_str: str, history_date=None) -> frozendict:
    """
    See parse_filter_uncached
    """
    return parse_filter_uncached(filter_str, history_date)


def translate_connection_label_in_string(filter_str: str, match_adapter_name: str, client_labels: list, ) -> str:
    """
    This method finds the connection label parts in the given filter string and translates it
    :param filter_str: The filter string to translate
    :param match_adapter_name: Adapter name of the match filter (The chosen adapter for asset entity filter)
    :param client_labels: List of all the client labels
    :return:
    """

    # This prevents some looping imports
    from axonius.consts.adapter_consts import CONNECTION_LABEL

    query_connection_label_equal = f'{CONNECTION_LABEL} =='
    query_connection_label_exist = f'{CONNECTION_LABEL} == ({{"$exists":true,"$ne":""}})))'
    query_connection_label_in = f'{CONNECTION_LABEL} in'

    def create_client_id_and_plugin_name_condition(client_id, plugin_unique_name) -> str:
        """

        Transform condition base 'specific_data.connection_label' to compound condition match build from:
         ('specific_data.client_used === <client_id> AND 'specific_data.plugin_unique_name == <plugin_unique_name>)

        :param client_id:  adapter client id
        :param plugin_unique_name: adapter unique name
        :return: transform filter string
        """
        client_used_field = CLIENT_USED if match_adapter_name else SPECIFIC_DATA_CLIENT_USED
        plugin_unique_name_field = PLUGIN_UNIQUE_NAME if match_adapter_name else SPECIFIC_DATA_PLUGIN_UNIQUE_NAME

        return f'({client_used_field} == "{client_id}" ' \
               f'and {plugin_unique_name_field} == "{plugin_unique_name}" )'

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

    def create_label_condition(adapter_filter: str, label: str) -> str:
        """
        A Label can match multiple clients .
        client_info  = ( <client_id> , <plugin_unique_name> )

        :param adapter_filter: The adapter name for which the connection label filter is applied
        :param label: a AQL adapter connection label
        :return: AQL filter string compatible
        """
        # if adapter name provided, we fetch only its relevant labels, otherwise we get all labels
        relevant_labels = [client for client in client_labels.get(label, [])
                           if client and len(client) > 1 and client[1].startswith(adapter_filter)]
        labels_info = [create_client_id_and_plugin_name_condition(client_id, name) for (client_id, name) in
                       relevant_labels]
        if labels_info:
            return create_or_separated_condition(labels_info)
        return f'{SPECIFIC_DATA_CLIENT_USED} == []'

    def extract_adapter_name(filter_string: str):
        """
        Get the adapter name from the filter string.
        For example: If the input is '(adapters_data.json_file_adapter.connection_label == "some value")',
        The output will be 'json_file_adapter'.
        If no adapter data exists, an empty string is returned.
        :param filter_string: The current filter string to search from
        :return: The adapter name for which the connection label filter is applied
        """
        extracted_adapter_name = ''
        adapter_name_matcher = re.search(fr'{ADAPTERS_DATA}\.(\w+)', filter_string)
        if adapter_name_matcher:
            extracted_adapter_name = adapter_name_matcher.group(1)
        return extracted_adapter_name

    # transform operator exists with compound condition of all labels filtered by selected adapter name (if selected)
    if query_connection_label_exist in filter_str:
        exists_regexp = re.escape('({"$exists":true,"$ne":""})))')
        matcher = re.search(fr'\(\(\w+.\w+\.{CONNECTION_LABEL} == {exists_regexp}', filter_str)
        while matcher:
            adapter_name = match_adapter_name if match_adapter_name else extract_adapter_name(matcher.group(0))
            client_labels_ids = client_labels.values()
            client_details = [create_client_id_and_plugin_name_condition(client_id, name) for ids in client_labels_ids
                              for client_id, name in ids if name.startswith(adapter_name)]
            # If no client details were found, we send empty client details to the query so no matches will be found
            if not client_details:
                client_details = [create_client_id_and_plugin_name_condition('', '')]
            all_connection_labels_condition = create_or_separated_condition(client_details)
            filter_str = filter_str.replace(matcher.group(0), all_connection_labels_condition)
            matcher = re.search(fr'\(\(\w+.\w+\.{CONNECTION_LABEL} == {exists_regexp}', filter_str)

    # # transform operator 'in' with new compound condition per client in OR logic
    if query_connection_label_in in filter_str:
        matcher = re.search(fr'\w+.\w+\.{CONNECTION_LABEL}' + r' in \[(.+?)\]', filter_str)
        while matcher:
            adapter_name = match_adapter_name if match_adapter_name else extract_adapter_name(matcher.group(0))
            filter_labels = matcher.group(1)
            labels_list = [label.strip('"') for label in filter_labels.split(',')]
            label_attributes = [create_label_condition(adapter_name, label) for label in labels_list]
            filter_str = filter_str.replace(matcher.group(0), create_or_separated_condition(label_attributes))

            # in case of complex conditions
            matcher = re.search(fr'\w+.\w+\.{CONNECTION_LABEL}' + r' in \[(.+?)\]', filter_str)

    # transform operator equal with compound condition to match (client_id,plugin_unique_name) tuple
    if query_connection_label_equal in filter_str:
        matcher = re.search(fr'\w+.\w+\.{CONNECTION_LABEL} == \"(.+?)\"', filter_str)
        while matcher:
            adapter_name = match_adapter_name if match_adapter_name else extract_adapter_name(matcher.group(0))
            filter_str = filter_str.replace(matcher.group(0), create_label_condition(adapter_name, matcher.group(1)))
            matcher = re.search(fr'\w+.\w+\.{CONNECTION_LABEL} == \"(.+?)\"', filter_str)

    return filter_str


def translate_from_connection_labels(filter_str: str) -> str:
    # This prevents some looping imports
    from axonius.plugin_base import PluginBase

    def extract_adapter_name_from_match(match_string):
        pattern = r'plugin_name == \'(.+?)\''
        match = re.search(pattern, match_string)
        if match:
            return match.group(1)
        return ''

    def get_match_filter_strings(filter_string: str):
        """
        Returns a list of match filter string from the entire given filter string.
        For example: If the input is 'specific_data == match([plugin_name == 'active_directory_adapter'
        and (data.connection_label == "or ad")]) and (specific_data.data.name == regex("D", "i"))
        and specific_data == match([plugin_name == 'json_file_adapter' and (data.hostname == "H")])'
        The returned list would be:
        [([plugin_name == 'active_directory_adapter' and (data.connection_label == "or ad")]),
         ([plugin_name == 'json_file_adapter' and (data.hostname == "H")])]
        :param filter_string: The entire filter string to search from
        :return: List of match filter strings
        """
        match_filters_strings = []
        for m in re.finditer('match', filter_string):
            match_filter_string = '('
            index = m.end() + 1
            parentheses_weight = 1
            while parentheses_weight:
                current_character = filter_string[index]
                match_filter_string += current_character
                if current_character == '(':
                    parentheses_weight += 1
                elif current_character == ')':
                    parentheses_weight -= 1
                index += 1
            match_filters_strings.append(match_filter_string)
        return match_filters_strings

    # Get all the client labels
    client_labels = PluginBase.Instance.clients_labels()

    # First of all, we need to process any connection labels that exists inside a match filter (asset entity filter)
    match_filters = get_match_filter_strings(filter_str)

    # For each match filter, we translate every connection label filter if it appears there
    for match_filter in match_filters:
        adapter_name = extract_adapter_name_from_match(match_filter)
        translated_match_filter = translate_connection_label_in_string(match_filter, adapter_name, client_labels)
        filter_str = filter_str.replace(match_filter, translated_match_filter)

    return translate_connection_label_in_string(filter_str, '', client_labels)


def translate_os_distribution_gt_lt_filter(filter_str: str) -> str:
    """
    Translates the relational operators '>' and '<' that are applied to os distribution to 'IN' operator
    For example: If the given input is '(specific_data.data.os.distribution > "Server 2012 R2")'
    The resulted output will contain all values of windows versions bigger than "Server 2012 R2" and
    will look like that: '(specific_data.data.os.distribution in ["10","Server 2016","Server 2019"])'
    Note! This works only for windows versions as of now.
    :param filter_str: The filter string to translate
    """
    matcher = re.search(OS_DISTRIBUTION_GT_LT_QUERY_REGEX, filter_str)
    while matcher:
        os_distribution = matcher.group(2)
        comp_operator = matcher.group(1)
        distribution_enum_index = ENUM_WINDOWS_VERSIONS.index(os_distribution)
        if comp_operator == '<':
            relevant_os_distributions = ENUM_WINDOWS_VERSIONS[distribution_enum_index + 1:]
        else:
            relevant_os_distributions = ENUM_WINDOWS_VERSIONS[:distribution_enum_index]
        translated_filter = 'os.distribution in [' \
                            + ','.join('"{0}"'.format(version) for version in relevant_os_distributions) + ']'
        filter_str = filter_str.replace(matcher.group(0), translated_filter)
        matcher = re.search(OS_DISTRIBUTION_GT_LT_QUERY_REGEX, filter_str)

    return filter_str


def parse_filter(filter_str: str, history_date=None, entity=None) -> dict:
    """
    If given filter contains the keyword NOW, meaning it needs a calculation relative to current date,
    it must be recalculated, instead of using the cached result
    """
    # prevents looping imports
    from axonius.consts.adapter_consts import CONNECTION_LABEL

    filter_str = replace_saved_queries_ids(filter_str, entity)
    if filter_str and (OS_DISTRIBUTION_LT_SUFFIX in filter_str or OS_DISTRIBUTION_GT_SUFFIX in filter_str):
        filter_str = translate_os_distribution_gt_lt_filter(filter_str)
    if filter_str and CONNECTION_LABEL in filter_str:
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

        labels = entity['labels'] if 'labels' in entity else []
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
                            if tag['type'] == 'data' and 'data' in tag and tag['data'] is not False]
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
            HAS_NOTES: entity.get(HAS_NOTES),
            'adapters': adapters,
            'labels': labels,
            PREFERRED_FIELDS: entity.get(PREFERRED_FIELDS),
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

        if field in ['adapters']:
            continue
        if splitted[0] == SPECIFIC_DATA:
            splitted[0] = 'adapters'
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


def replace_saved_queries_ids(aql_filter: str, entity_type) -> str:
    """
    This method receives a filter as string, and replace all saved queries ids with the
    actual aql if needed. Iterate the filter until no matches found - instead of iterating
    it recursively.
    :param aql_filter: filter as string
    :param entity_type:
    :return: replaces filter, or the same one.
    """

    # This prevents some looping imports
    from axonius.plugin_base import PluginBase

    if bool(aql_filter) and entity_type:
        collection = PluginBase.Instance.gui_dbs.entity_query_views_db_map[entity_type]
        matches = re.findall(SAVED_QUERY_PLACEHOLDER_REGEX, aql_filter)
        already_replaced_matches = {}
        while matches:
            for query_id in matches:
                value = None
                if query_id in already_replaced_matches:
                    value = already_replaced_matches[query_id]
                else:
                    query = collection.find_one({
                        '_id': ObjectId(query_id)
                    }, projection={'view.query.filter': True})
                    if query:
                        value = query.get('view', {}).get('query', {}).get('filter', '')
                if value:
                    aql_filter = aql_filter.replace(f'{{{{QueryID={query_id}}}}}', value)
                    if query_id not in already_replaced_matches:
                        already_replaced_matches[query_id] = value
                else:
                    logger.error(f'ERROR: Unable to find match for query {query_id}')
                    return aql_filter
            matches = re.findall(SAVED_QUERY_PLACEHOLDER_REGEX, aql_filter)
    return aql_filter
