import logging
from typing import List, Iterable, Tuple
from collections import defaultdict, Counter
from datetime import date, datetime, timedelta
from multiprocessing import cpu_count
from bson import ObjectId
from dateutil.parser import parse as parse_date

from axonius.consts.plugin_consts import PLUGIN_NAME
from axonius.consts.gui_consts import (ChartMetrics, ChartViews, ChartFuncs, ChartRangeTypes, ChartRangeUnits,
                                       ADAPTERS_DATA, SPECIFIC_DATA,
                                       RANGE_UNIT_DAYS,
                                       DASHBOARD_COLLECTION)
from axonius.entities import EntityType
from axonius.plugin_base import PluginBase, return_error
from axonius.utils.axonius_query_language import (convert_db_entity_to_view_entity, parse_filter)
from axonius.utils.gui_helpers import (find_filter_by_name, find_entity_field, get_string_from_field_value)
from axonius.utils.revving_cache import rev_cached, rev_cached_entity_type
from axonius.utils.threading import GLOBAL_RUN_AND_FORGET
from gui.gui_logic.db_helpers import beautify_db_entry

logger = logging.getLogger(f'axonius.{__name__}')


@rev_cached_entity_type(ttl=300)
def adapter_data(entity_type: EntityType):
    """
    See adapter_data
    """
    logger.info(f'Getting adapter data for entity {entity_type.name}')

    # pylint: disable=W0212
    entity_collection = PluginBase.Instance._entity_db_map[entity_type]
    adapter_entities = {
        'seen': 0, 'seen_gross': 0, 'unique': entity_collection.estimated_document_count(), 'counters': []
    }

    # First value is net adapters count, second is gross adapters count (refers to AX-2430)
    # If an Axonius entity has 2 adapter entities from the same plugin it will be counted for each time it is there
    entities_per_adapters = defaultdict(lambda: {'value': 0, 'meta': 0})
    for res in entity_collection.aggregate([{
            '$group': {
                '_id': f'$adapters.{PLUGIN_NAME}',
                'count': {
                    '$sum': 1
                }
            }
    }]):
        for plugin_name in set(res['_id']):
            entities_per_adapters[plugin_name]['value'] += res['count']
            adapter_entities['seen'] += res['count']

        for plugin_name in res['_id']:
            entities_per_adapters[plugin_name]['meta'] += res['count']
            adapter_entities['seen_gross'] += res['count']
    for name, value in entities_per_adapters.items():
        adapter_entities['counters'].append({'name': name, **value})

    return adapter_entities


def fetch_chart_compare(chart_view: ChartViews, views: List) -> List:
    """
    Iterate given views, fetch each one's filter from the appropriate query collection, according to its module,
    and execute the filter on the appropriate entity collection.

    :param chart_view:
    :param views: List of views to fetch data by for comparing results
    :return:
    """
    if not views:
        raise Exception('No views for the chart')

    data = []
    total = 0
    for view in views:
        # Can be optimized by taking all names in advance and querying each module's collection once
        # But since list is very short the simpler and more readable implementation is fine
        entity_name = view.get('entity', EntityType.Devices.value)
        entity = EntityType(entity_name)
        view_dict = find_filter_by_name(entity, view['name'])
        if not view_dict:
            continue

        data_item = {
            'name': view['name'],
            'view': view_dict,
            'module': entity_name,
            'value': 0
        }
        # pylint: disable=protected-access
        if view.get('for_date'):
            data_item['value'] = PluginBase.Instance._historical_entity_views_db_map[entity].count_documents(
                {
                    '$and': [
                        parse_filter(view_dict['query']['filter']), {
                            'accurate_for_datetime': view['for_date']
                        }
                    ]
                })
            data_item['accurate_for_datetime'] = view['for_date']
        else:
            data_item['value'] = PluginBase.Instance._entity_db_map[entity].count_documents(
                parse_filter(view_dict['query']['filter']))
        # pylint: enable=protected-access
        data.append(data_item)
        total += data_item['value']

    def val(element):
        return element.get('value', 0)

    data.sort(key=val, reverse=True)
    if chart_view == ChartViews.pie:
        return_data = [{'name': 'ALL', 'value': 0}]
        if total:
            return_data.extend(map(lambda x: {**x, 'value': x['value'] / total}, data))
        return return_data
    return data


def fetch_chart_intersect(_: ChartViews, entity: EntityType, base, intersecting, for_date=None) -> List:
    """
    This chart shows intersection of 1 or 2 'Child' views with a 'Parent' (expected not to be a subset of them).
    Module to be queried is defined by the parent query.

    :param _: Placeholder to create uniform interface for the chart fetching methods
    :param entity:
    :param base:
    :param intersecting: List of 1 or 2 views
    :param for_date: Data will be fetched and calculated according to what is stored on this date
    :return: List of result portions for the query executions along with their names. First represents Parent query.
             If 1 child, second represents Child intersecting with Parent.
             If 2 children, intersection between all three is calculated, namely 'Intersection'.
                            Second and third represent each Child intersecting with Parent, excluding Intersection.
                            Fourth represents Intersection.
    """
    if not intersecting or len(intersecting) < 1:
        raise Exception('Pie chart requires at least one views')
    # Query and data collections according to given parent's module
    # pylint: disable=protected-access
    data_collection = PluginBase.Instance._entity_db_map[entity]
    # pylint: enable=protected-access

    base_view = {'query': {'filter': '', 'expressions': []}}
    base_queries = []
    if base:
        base_view = find_filter_by_name(entity, base)
        if not base_view or not base_view.get('query'):
            return None
        base_queries = [parse_filter(base_view['query']['filter'])]

    if for_date:
        # If history requested, fetch from appropriate historical db
        # pylint: disable=protected-access
        data_collection = PluginBase.Instance._historical_entity_views_db_map[entity]
        # pylint: enable=protected-access
        base_queries.append({
            'accurate_for_datetime': for_date
        })

    data = []
    total = data_collection.count_documents({'$and': base_queries} if base_queries else {})
    if not total:
        return [{'name': base or 'ALL', 'value': 0, 'remainder': True,
                 'view': {**base_view, 'query': {'filter': base_view['query']['filter']}}, 'module': entity.value}]

    child1_view = find_filter_by_name(entity, intersecting[0])
    if not child1_view or not child1_view.get('query'):
        return None
    child1_filter = child1_view['query']['filter']
    child1_query = parse_filter(child1_filter)
    base_filter = f'({base_view["query"]["filter"]}) and ' if base_view['query']['filter'] else ''
    child2_filter = ''
    if len(intersecting) == 1:
        # Fetch the only child, intersecting with parent
        child1_view['query']['filter'] = f'{base_filter}({child1_filter})'
        data.append({'name': intersecting[0], 'view': child1_view, 'module': entity.value,
                     'value': data_collection.count_documents({
                         '$and': base_queries + [child1_query]
                     }) / total})
    else:
        child2_view = find_filter_by_name(entity, intersecting[1])
        if not child2_view or not child2_view.get('query'):
            return None
        child2_filter = child2_view['query']['filter']
        child2_query = parse_filter(child2_filter)

        # Child1 + Parent - Intersection
        child1_view['query']['filter'] = f'{base_filter}({child1_filter}) and not ({child2_filter})'
        data.append({'name': intersecting[0], 'value': data_collection.count_documents({
            '$and': base_queries + [
                child1_query,
                {
                    '$nor': [child2_query]
                }
            ]
        }) / total, 'module': entity.value, 'view': child1_view})

        # Intersection
        data.append(
            {'name': ' + '.join(intersecting),
             'intersection': True,
             'value': data_collection.count_documents({
                 '$and': base_queries + [
                     child1_query, child2_query
                 ]}) / total,
             'view': {**base_view, 'query': {'filter': f'{base_filter}({child1_filter}) and ({child2_filter})'}},
             'module': entity.value})

        # Child2 + Parent - Intersection
        child2_view['query']['filter'] = f'{base_filter}({child2_filter}) and not ({child1_filter})'
        data.append({'name': intersecting[1], 'value': data_collection.count_documents({
            '$and': base_queries + [
                child2_query,
                {
                    '$nor': [child1_query]
                }
            ]
        }) / total, 'module': entity.value, 'view': child2_view})

    remainder = 1 - sum([x['value'] for x in data])
    child2_or = f' or ({child2_filter})' if child2_filter else ''
    return [{'name': base or 'ALL', 'value': remainder, 'remainder': True, 'view': {
        **base_view, 'query': {'filter': f'{base_filter}not (({child1_filter}){child2_or})'}
    }, 'module': entity.value}, *data]


# pylint: disable-msg=too-many-locals
def _query_chart_segment_results(field_parent: str, view, entity: EntityType, for_date: datetime,
                                 filters_keys: list):
    """
    create aggregation object and return his results
    :param field_parent: field parent name
    :param view:
    :param entity: entity to query
    :param for_date: date restrictions
    :param filters_keys: a list of all filter by keys ( field names to filter by )
    :return: aggregation results
    """
    base_view = {'query': {'filter': '', 'expressions': []}}
    base_queries = []
    if view:
        base_view = find_filter_by_name(entity, view)
        if not base_view or not base_view.get('query'):
            return None, None
        base_queries.append(parse_filter(base_view['query']['filter']))
    # pylint: disable=protected-access
    data_collection = PluginBase.Instance._entity_db_map[entity]
    if for_date:
        # If history requested, fetch from appropriate historical db
        data_collection = PluginBase.Instance._historical_entity_views_db_map[entity]
        base_queries.append({
            'accurate_for_datetime': for_date
        })
    # pylint: enable=protected-access
    base_query = {
        '$and': base_queries
    } if base_queries else {}

    adapter_conditions = [
        {
            '$ne': ['$$i.data._old', True]
        }
    ]
    empty_field_name = ''
    # prepare field parent name
    if field_parent.startswith(SPECIFIC_DATA):
        empty_field_name = '.' + field_parent[len(SPECIFIC_DATA) + 1:]

    elif field_parent.startswith(ADAPTERS_DATA):
        # e.g. adapters_data.aws_adapter.some_field
        splitted = field_parent.split('.')
        adapter_data_adapter_name = splitted[1]

        # this condition is specific for fields that are in a specific adapter, so we
        # will not take other adapters that might share a field name (although the field itself might differ)
        adapter_conditions.append({
            '$eq': [f'$$i.{PLUGIN_NAME}', adapter_data_adapter_name]
        })
        empty_field_name = '.data.' + '.'.join(splitted[2:]) if len(splitted) > 2 else '.data'

    adapter_parent_field_name = '$adapters' + empty_field_name
    tags_parent_field_name = '$tags' + empty_field_name

    # prepare list of inputs for filtering requested data ( single or multiple fields )
    filter_inputs = []
    # prepare list of reduce function one for each field name
    unique_values_inputs = []
    # prepare name pattern
    name_pattern = {}
    # iterate and fill variables
    for index, filter_key in enumerate(filters_keys):
        name_pattern[filter_key] = {'$arrayElemAt': ['$unique_values', index]}
        unique_values_inputs.append(_generate_aggregate_unique_values_reduce(filter_key))
        filter_inputs.append(
            _generate_aggregate_combine_inputs_reduce(adapter_parent_field_name,
                                                      tags_parent_field_name,
                                                      filter_key))
    name_pattern['doc_id'] = {'$toString': '$_id'}

    query = [
        # match base queries
        {
            '$match': base_query
        },
        # filter old data from adapters
        {
            '$project': {
                'tags': '$tags',
                'adapters': {
                    '$filter': {
                        'input': '$adapters',
                        'as': 'i',
                        'cond': {
                            '$and': adapter_conditions
                        }
                    }
                }
            }
        },
        # collect all data available by filters
        {
            '$project': {
                'collected_data': {
                    '$filter': {
                        'input': {
                            '$zip': {
                                'inputs': filter_inputs
                            }
                        },
                        'as': 'i',
                        'cond': {
                            '$ne': ['$$i', []]
                        }
                    }
                }
            }
        },
        # create unique array of objects representing the document data
        # each object contain a kev value pair/'s of field_name:actual_value
        {
            '$project': {
                'unique_values': {
                    '$setUnion': [
                        {
                            '$zip': {
                                'inputs': unique_values_inputs,
                                'useLongestLength': True
                            }
                        }
                    ]
                }
            }
        },
        # filter all objects containing null,
        # this can happen when no field is found in the previous stage
        # this behavior keeps the pairs synced and need to be removed in this stage and not before
        {
            '$project': {
                'unique_values': {
                    '$filter': {
                        'input': '$unique_values',
                        'as': 'i',
                        'cond': {'$allElementsTrue': ['$$i']}
                    }
                }
            }
        },
        # unwind to create a document for each object in the unique values array
        # we keeps the null for counting 'No Value' results
        {
            '$unwind': {
                'path': '$unique_values',
                'preserveNullAndEmptyArrays': True
            }
        },
        # group all documents by the unique values object to get the count
        # add extra_data array field for filtering the data
        # for each count, an object with the data will be in the array note: when the filter will be applied
        # each object that wont pass the filter should be deduct from the total count
        {
            '$group': {
                '_id': {
                    'name': {'$ifNull': [{'$arrayElemAt': ['$unique_values', 0]}, None]},
                    'doc_id': {'$toString': '$_id'}
                },
                'count': {'$sum': 1},
                'extra_data': {
                    '$push': {
                        '$cond': {
                            'if': {'$eq': [{'$arrayElemAt': ['$unique_values', 0]}, None]},
                            'then': 'No Value',
                            'else': name_pattern
                        }
                    }
                }
            }
        }
    ]
    # create the query
    logger.info(f'segmentation aggregation query:{query}')
    # execute!
    return base_view, data_collection.aggregate(query, allowDiskUse=True)


# pylint: disable-msg=too-many-branches
def fetch_chart_segment(chart_view: ChartViews, entity: EntityType, view, field, value_filter: list = None,
                        include_empty: bool = False, for_date=None) -> List:
    """
    Perform aggregation which matching given view's filter and grouping by given fields, in order to get the
    number of results containing each available value of the field.
    For each such value, add filter combining the original filter with restriction of the field to this value.
    If the requested view is a pie, divide all found quantities by the total amount, to get proportions.

    :return: Data counting the amount / portion of occurrences for each value of given field, among the results
            of the given view's filter
    """
    # parse field name
    # rpartition docs : https://docs.python.org/3.6/library/stdtypes.html#str.rpartition
    field_name_partition = field['name'].rpartition('.')
    field_parent = field_name_partition[0] or ''
    field_name = field_name_partition[2]
    if not value_filter:
        value_filter = []
    # backward compatibility: old filters used to be strings
    if isinstance(value_filter, str):
        value_filter = [
            {'name': field_name, 'value': value_filter}
        ]
    # remove unnamed filters
    value_filter = [x for x in value_filter if x['name']]
    # add default filter ( field name with '' as value to search)
    value_filter = [{'name': field_name, 'value': ''}] + value_filter
    # create merged filter object by uniq filter key ( field name )
    # rpartition docs : https://docs.python.org/3.6/library/stdtypes.html#str.rpartition
    reduced_filters = defaultdict(list)
    for item in value_filter:
        reduced_filters[item['name'].rpartition('.')[2]].append(item['value'])
    # remove empty search value,
    # this value if exist with another value at the same array can make the string query not valid
    for key, value in reduced_filters.items():
        if len(value) > 1:
            reduced_filters[key] = [x for x in value if x]
    # Query and data collections according to given module
    base_view, aggregate_results = _query_chart_segment_results(field_parent, view, entity, for_date,
                                                                filters_keys=[*reduced_filters])
    if not base_view or not aggregate_results:
        return None
    base_filter = f'({base_view["query"]["filter"]}) and ' if base_view['query']['filter'] else ''
    counted_results = Counter()
    for item in aggregate_results:
        result_name = item.get('_id', {}).get('name', 'No Value')
        extra_data = item.get('extra_data', [])
        if 'No Value' in extra_data:
            counted_results['No Value'] += 1
        elif _match_result_item_to_filters(extra_data, reduced_filters):
            counted_results[result_name] += 1

    data = []
    for result_name, result_count in counted_results.items():
        if result_name == 'No Value':
            if not include_empty or ''.join(reduced_filters[field_name]):
                continue
            query_filter = f'not ({field_parent}.{field_name} == exists(true))'
        else:
            query_filter = _generate_segmented_query_filter(result_name,
                                                            reduced_filters,
                                                            field_parent,
                                                            field_name)
        data.append({
            'name': result_name,
            'value': result_count,
            'module': entity.value,
            'view': {
                **base_view,
                'query': {
                    'filter': f'{base_filter}{query_filter}'
                }
            }
        })
    data = sorted(data, key=lambda x: x['value'], reverse=True)
    if chart_view == ChartViews.pie:
        total = sum([x['value'] for x in data])
        return [{'name': view or 'ALL', 'value': 0}, *[{**x, 'value': x['value'] / total} for x in data]]
    return data


def _match_result_item_to_filters(extra_data: list, filters: dict) -> bool:
    """
    check if the row returned from the aggregation stage is legit by requested filters
    :param extra_data: list of dicts for each count the result got in the aggregation
    :param filters: key value pair of: key -> filter (field) name, value -> list of requirements to match
    :return: boolean representing if item pass the check
    """
    is_item_legit = False
    # for each set of result, expected only one.
    # its because the aggregation must output a list in the group stage
    for data in extra_data:
        is_valid = True
        # for each requested filter name
        for filter_name in filters:
            # the user can ask several matches to the field
            # if one match not exist the item wont pass this test
            for match in filters[filter_name]:
                try:
                    # we come across an error when the data in extra data is not in a form of dict
                    # wrap it in try expect and log the error for further investigations
                    if match.lower() not in get_string_from_field_value(data[filter_name]).lower():
                        is_valid = False
                except TypeError:
                    logger.error(f'segmentation data return unexpected type:{type(data)} data:{data} '
                                 f'extra data:{extra_data} filter_name:{filter_name}')
                    is_valid = False
        if is_valid:
            is_item_legit = True
    return is_item_legit


def _generate_segmented_query_filter(result_name, filters, field_parent, segmented_field_name):
    """
    generate query string for the use in devices/users page, per result given
    :param result_name: the result name of the requested segmentation
    :param filters: the filter to apply in the query string
    :param field_parent: the name of the segmented field
    :param segmented_field_name: the name of the segmented field, used to discard filters
    :return: query string composed from the segmented field query and a match query list of filters
    """
    query_filters = []
    segment_field_name = '.'.join([field_parent, segmented_field_name]) if field_parent else segmented_field_name
    segment_filter = _generate_segmented_field_query_filter(segment_field_name, result_name)
    for field_name, field_value in filters.items():
        # Build the filter, according to the supported types
        if field_name == segmented_field_name:
            continue
        for value in field_value:
            if value:
                query_filters.append(_generate_segmented_field_query_filter(field_name, value, True))

    if len(query_filters) > 0:
        wrapped_query_filters = [f'({x})' for x in query_filters]
        return f'{segment_filter} and ({field_parent} == match([{" and ".join(wrapped_query_filters)}]))'
    return segment_filter
# pylint: enable-msg=too-many-branches


def _generate_segmented_field_query_filter(field_name, value, with_regex=False):
    """
    generate query string for one field name and value pair, can produce string for compare and contain methods
    :param field_name: field name to use in the string
    :param value: the value of compare or contain
    :param with_regex: use contain in true and compare in false
    :return: one name value pair query string
    """
    query_filter = ''
    if isinstance(value, str):
        if value in ['false', 'true']:
            query_filter = f'{field_name} == {value}'
        else:
            if with_regex:
                query_filter = f'{field_name} == regex("{value}","i")'
            else:
                query_filter = f'{field_name} == "{value}"'
    elif isinstance(value, int):
        query_filter = f'{field_name} == {value}'
    elif isinstance(value, datetime):
        query_filter = f'{field_name} == date("{value}")'
    return query_filter


def _generate_aggregate_combine_inputs_reduce(field_adapter_parent, field_tags_parent, key):
    """
    generate reduce object for the aggregation stage per filter
    the reduce take the parent as array and return key value object with the filter name as key
    and the original value of the document in that key, as value
    :param field_adapter_parent: the adapter parent field name of the requested filter (field name)
    :param field_tags_parent: the tags parent field name of the requested filter (field name)
    :param key: the key to use in the reduce ( equivalent to field name )
    :return: object representing one filter reduce to be in array of reduces
    """
    field_name = field_key = key
    if field_key == 'labels':
        field_key = 'name'
    return {
        '$reduce': {
            'input': {
                '$setUnion': [
                    f'{field_adapter_parent}',
                    f'{field_tags_parent}'
                ]
            },
            'initialValue': [],
            'in': {
                '$concatArrays': [
                    '$$value', {
                        '$map': {
                            'input': {
                                '$cond': {
                                    'if': {'$isArray': ['$$this']},
                                    'then': '$$this',
                                    'else': ['$$this']
                                }
                            },
                            'as': 'i',
                            'in': {
                                f'{field_name}': {'$ifNull': [f'$$i.{field_key}', None]}
                            }
                        }
                    }
                ]
            }
        }
    }


def _generate_aggregate_unique_values_reduce(key):
    """
    generate reduce object for the aggregation stage per filter
    the reduce take the collected data array and create array of object representing filter name results
    this reduce is part of zip function that will create zip version of all this reduces
    :param key: the filter name ( field name ) to
    :return: object representing one array of objects to zip
    """
    return {
        '$reduce': {
            'input': {
                '$reduce': {
                    'input': '$collected_data',
                    'initialValue': [],
                    'in': {
                        '$concatArrays': [
                            '$$value', {
                                '$cond': [
                                    {'$isArray': f'$$this.{key}'},
                                    f'$$this.{key}',
                                    [f'$$this.{key}']
                                ]
                            }
                        ]
                    }
                }
            },
            'initialValue': [],
            'in': {
                '$concatArrays': [
                    '$$value', {
                        '$cond': {
                            'if': {'$isArray': ['$$this']},
                            'then': '$$this',
                            'else': [
                                {
                                    '$cond': [
                                        {'$eq': [{'$type': '$$this'}, 'bool']},
                                        {'$toString': '$$this'},
                                        '$$this'
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }


def _query_chart_abstract_results(field: dict, entity: EntityType, view, for_date: datetime):
    """
    Build the query and retrieve data for calculating the abstract chart for given field and view
    """
    splitted = field['name'].split('.')
    additional_elemmatch_data = {}

    if splitted[0] == SPECIFIC_DATA:
        processed_field_name = '.'.join(splitted[1:])
    elif splitted[0] == ADAPTERS_DATA:
        processed_field_name = 'data.' + '.'.join(splitted[2:])
        additional_elemmatch_data = {
            PLUGIN_NAME: splitted[1]
        }
    else:
        raise Exception(f'Can\'t handle this field {field["name"]}')

    adapter_field_name = 'adapters.' + processed_field_name
    tags_field_name = 'tags.' + processed_field_name

    base_view = {'query': {'filter': ''}}
    base_query = {
        '$or': [
            {
                'adapters': {
                    '$elemMatch': {
                        processed_field_name: {
                            '$exists': True
                        },
                        **additional_elemmatch_data
                    }
                }
            },
            {
                'tags': {
                    '$elemMatch': {
                        processed_field_name: {
                            '$exists': True
                        },
                        **additional_elemmatch_data
                    }
                }
            }
        ]
    }
    if view:
        base_view = find_filter_by_name(entity, view)
        if not base_view or not base_view.get('query'):
            return None, None
        base_query = {
            '$and': [
                parse_filter(base_view['query']['filter']),
                base_query
            ]
        }
        base_view['query']['filter'] = f'({base_view["query"]["filter"]}) and ' if view else ''

    field_compare = 'true' if field['type'] == 'bool' else 'exists(true)'
    if field['type'] in ['number', 'integer']:
        field_compare = f'{field_compare} and {field["name"]} > 0'
    base_view['query']['filter'] = f'{base_view["query"]["filter"]}{field["name"]} == {field_compare}'

    # pylint: disable=protected-access
    data_collection = PluginBase.Instance._entity_db_map[entity]
    if for_date:
        # If history requested, fetch from appropriate historical db
        data_collection = PluginBase.Instance._historical_entity_views_db_map[entity]
        base_query = {
            '$and': [
                base_query, {
                    'accurate_for_datetime': for_date
                }
            ]
        }
    # pylint: enable=protected-access
    return base_view, data_collection.find(base_query, projection={
        adapter_field_name: 1,
        tags_field_name: 1,
        f'adapters.{PLUGIN_NAME}': 1,
        f'tags.{PLUGIN_NAME}': 1
    })


def fetch_chart_abstract(_: ChartViews, entity: EntityType, view, field, func, for_date=None):
    """
    One piece of data summarizing the given field's values resulting from given view's query, according to given func
    """
    # Query and data collections according to given module

    field_name = field['name']
    base_view, results = _query_chart_abstract_results(field, entity, view, for_date)
    if not base_view or not results:
        return None
    count = 0
    sigma = 0
    for item in results:
        field_values = find_entity_field(convert_db_entity_to_view_entity(item, ignore_errors=True), field_name)
        if not field_values or (isinstance(field_values, list) and all(not val for val in field_values)):
            continue
        if ChartFuncs[func] == ChartFuncs.count:
            count += 1
            continue
        if isinstance(field_values, list):
            count += len(field_values)
            sigma += sum(field_values)
        else:
            count += 1
            sigma += field_values

    if not count:
        return [{'name': view, 'value': 0, 'view': base_view, 'module': entity.value}]
    name = f'{func} of {field["title"]} on {view or "ALL"} results'
    if ChartFuncs[func] == ChartFuncs.average:
        return [
            {'name': name, 'value': (sigma / count), 'schema': field, 'view': base_view, 'module': entity.value}]
    return [{'name': name, 'value': count, 'view': base_view, 'module': entity.value}]


def _parse_range_timeline(timeframe):
    """
    Timeframe dict includes choice of range for the timeline chart.
    It can be absolute and include a date to start and to end the series,
    or relative and include a unit and count to fetch back from moment of request.

    :param timeframe:
    :return:
    """
    try:
        range_type = ChartRangeTypes[timeframe['type']]
    except KeyError:
        logger.error(f'Unexpected timeframe type {timeframe["type"]}')
        return None, None
    if range_type == ChartRangeTypes.absolute:
        logger.info(f'Gathering data between {timeframe["from"]} and {timeframe["to"]}')
        try:
            date_to = parse_date(timeframe['to'])
            date_from = parse_date(timeframe['from'])
        except ValueError:
            logger.exception('Given date to or from is invalid')
            return None, None
    else:
        logger.info(f'Gathering data from {timeframe["count"]} {timeframe["unit"]} back')
        date_to = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            range_unit = ChartRangeUnits[timeframe['unit']]
        except KeyError:
            logger.error(f'Unexpected timeframe unit {timeframe["unit"]} for reltaive chart')
            return None, None
        date_from = date_to - timedelta(days=timeframe['count'] * RANGE_UNIT_DAYS[range_unit])
    return date_from, date_to


def _get_date_ranges(start: datetime, end: datetime) -> Iterable[Tuple[date, date]]:
    """
    Generate date intervals from the given datetimes according to the amount of threads
    """
    start = start.date()
    end = end.date()

    thread_count = min([cpu_count(), (end - start).days]) or 1
    interval = (end - start) / thread_count

    for i in range(thread_count):
        start = start + (interval * i)
        end = start + (interval * (i + 1))
        yield (start, end)


def _compare_timeline_lines(views, date_ranges):
    for view in views:
        if not view.get('name'):
            continue
        entity = EntityType(view['entity'])
        base_view = find_filter_by_name(entity, view['name'])
        if not base_view or not base_view.get('query'):
            return
        yield {
            'title': view['name'],
            'points': _fetch_timeline_points(entity, parse_filter(base_view['query']['filter']), date_ranges)
        }


def _intersect_timeline_lines(views, date_ranges):
    if len(views) != 2 or not views[0].get('name'):
        logger.error(f'Unexpected number of views for performing intersection {len(views)}')
        yield {}
    first_entity_type = EntityType(views[0]['entity'])
    second_entity_type = EntityType(views[1]['entity'])

    # first query handling
    base_query = {}
    if views[0].get('name'):
        base_view = find_filter_by_name(first_entity_type, views[0]['name'])
        if not base_view or not base_view.get('query'):
            return
        base_query = parse_filter(base_view['query']['filter'])
    yield {
        'title': views[0]['name'],
        'points': _fetch_timeline_points(first_entity_type, base_query, date_ranges)
    }

    # second query handling
    intersecting_view = find_filter_by_name(second_entity_type, views[1]['name'])
    if not intersecting_view or not intersecting_view.get('query'):
        yield {}
    intersecting_query = parse_filter(intersecting_view['query']['filter'])
    if base_query:
        intersecting_query = {
            '$and': [
                base_query, intersecting_query
            ]
        }
    yield {
        'title': f'{views[0]["name"]} and {views[1]["name"]}',
        'points': _fetch_timeline_points(second_entity_type, intersecting_query, date_ranges)
    }


def _fetch_timeline_points(entity_type: EntityType, match_query, date_ranges):
    # pylint: disable=protected-access
    def aggregate_for_date_range(args):
        range_from, range_to = args
        return PluginBase.Instance._historical_entity_views_db_map[entity_type].aggregate([
            {
                '$match': {
                    '$and': [
                        match_query, {
                            'accurate_for_datetime': {
                                '$lte': datetime.combine(range_to, datetime.min.time()),
                                '$gte': datetime.combine(range_from, datetime.min.time())
                            }
                        }
                    ]
                }
            }, {
                '$group': {
                    '_id': '$accurate_for_datetime',
                    'count': {
                        '$sum': 1
                    }
                }
            }
        ])

    # pylint: enable=protected-access
    points = {}
    for results in list(GLOBAL_RUN_AND_FORGET.map(aggregate_for_date_range, date_ranges)):
        for item in results:
            # _id here is the grouping id, so in fact it is accurate_for_datetime
            points[item['_id'].strftime('%m/%d/%Y')] = item.get('count', 0)
    return points


def fetch_chart_timeline(_: ChartViews, views, timeframe, intersection=False):
    """
    Fetch and count results for each view from given views, per day in given timeframe.
    Timeframe can be either:
    - Absolute - defined by a start and end date to fetch between
    - Relative - defined by a unit (days, weeks, months, years) and an amount, to fetch back from now
    Create for each view a sequence of points that represent the count for each day in the range.

    :param views: List of view for which to fetch results over timeline
    :param dateFrom: Date to start fetching from
    :param dateTo: Date to fetch up to
    :return:
    """
    date_from, date_to = _parse_range_timeline(timeframe)
    if not date_from or not date_to:
        return None
    date_ranges = list(_get_date_ranges(date_from, date_to))
    if intersection:
        lines = list(_intersect_timeline_lines(views, date_ranges))
    else:
        lines = list(_compare_timeline_lines(views, date_ranges))
    if not lines:
        return None

    scale = [(date_from + timedelta(i)) for i in range((date_to - date_from).days + 1)]
    return [
        ['Day'] + [{
            'label': line['title'],
            'type': 'number'
        } for line in lines],
        *[[day] + [line['points'].get(day.strftime('%m/%d/%Y')) for line in lines] for day in scale]
    ]


def generate_dashboard_uncached(dashboard_id: ObjectId):
    """
    See _get_dashboard
    """
    # pylint: disable=protected-access
    dashboard = PluginBase.Instance._get_collection(DASHBOARD_COLLECTION).find_one({
        '_id': dashboard_id
    })
    # pylint: enable=protected-access

    handler_by_metric = {
        ChartMetrics.compare: fetch_chart_compare,
        ChartMetrics.intersect: fetch_chart_intersect,
        ChartMetrics.segment: fetch_chart_segment,
        ChartMetrics.abstract: fetch_chart_abstract,
        ChartMetrics.timeline: fetch_chart_timeline
    }
    config = {**dashboard['config']}
    try:
        dashboard_metric = ChartMetrics[dashboard['metric']]
        if config.get('entity') and ChartMetrics.compare != dashboard_metric:
            # _fetch_chart_compare crashed in the wild because it got entity as a param.
            # We don't understand how such a dashboard chart was created. But at least we won't crash now
            config['entity'] = EntityType(dashboard['config']['entity'])
        dashboard['data'] = handler_by_metric[dashboard_metric](ChartViews[dashboard['view']], **config)
        if dashboard['data'] is None:
            dashboard['data'] = []
            logger.error(f'Problematic queries in dashboard {dashboard}')
    except Exception:
        dashboard['data'] = []
        logger.exception(f'Problem handling dashboard {dashboard}')
    dashboard['space'] = str(dashboard['space'])
    return beautify_db_entry(dashboard)


# there's no trivial way to remove the TTL functionality entirely, so let's just make it long enough
@rev_cached(ttl=3600 * 6)
def generate_dashboard(dashboard_id: ObjectId):
    """
    See _get_dashboard
    """
    return generate_dashboard_uncached(dashboard_id)


def fetch_latest_date(entity: EntityType, from_given_date: datetime, to_given_date: datetime):
    """
    For given entity and dates, check which is latest date with historical data, within the range
    """
    # pylint: disable=protected-access
    historical = PluginBase.Instance._historical_entity_views_db_map[entity]
    # pylint: enable=protected-access
    latest_date = historical.find_one({
        'accurate_for_datetime': {
            '$lt': to_given_date,
            '$gt': from_given_date,
        }
    }, sort=[('accurate_for_datetime', -1)], projection=['accurate_for_datetime'])
    if not latest_date:
        return None
    return latest_date['accurate_for_datetime']


def fetch_chart_intersect_historical(card, from_given_date, to_given_date):
    if not card.get('config') or not card['config'].get('entity') or not card.get('view'):
        return []
    config = {**card['config'], 'entity': EntityType(card['config']['entity'])}
    latest_date = fetch_latest_date(config['entity'], from_given_date, to_given_date)
    if not latest_date:
        return []
    return fetch_chart_intersect(ChartViews[card['view']], **config, for_date=latest_date)


def fetch_chart_compare_historical(card, from_given_date, to_given_date):
    """
    Finds the latest saved result from the given view list (from card) that are in the given date range
    """
    if not card.get('view') or not card.get('config') or not card['config'].get('views'):
        return []
    historical_views = []
    for view in card['config']['views']:
        view_name = view.get('name')
        if not view.get('entity') or not view_name:
            continue
        try:
            latest_date = fetch_latest_date(EntityType(view['entity']), from_given_date, to_given_date)
            if not latest_date:
                continue
            historical_views.append({'for_date': latest_date, **view})

        except Exception:
            logger.exception(f'When dealing with {view_name} and {view["entity"]}')
            continue
    if not historical_views:
        return []
    return fetch_chart_compare(ChartViews[card['view']], historical_views)


def fetch_chart_segment_historical(card, from_given_date, to_given_date):
    """
    Get historical data for card of metric 'segment'
    """
    if not card.get('view') or not card.get('config') or not card['config'].get('entity'):
        return []
    config = {**card['config'], 'entity': EntityType(card['config']['entity'])}
    latest_date = fetch_latest_date(config['entity'], from_given_date, to_given_date)
    if not latest_date:
        return []
    return fetch_chart_segment(ChartViews[card['view']], **config, for_date=latest_date)


def fetch_chart_abstract_historical(card, from_given_date, to_given_date):
    """
    Get historical data for card of metric 'abstract'
    """
    config = {**card['config'], 'entity': EntityType(card['config']['entity'])}
    latest_date = fetch_latest_date(config['entity'], from_given_date, to_given_date)
    if not latest_date:
        return []
    return fetch_chart_abstract(ChartViews[card['view']], **config, for_date=latest_date)


def dashboard_historical_uncached(dashboard_id: ObjectId, from_date: datetime, to_date: datetime):
    # pylint: disable=protected-access
    dashboard = PluginBase.Instance._get_collection(DASHBOARD_COLLECTION).find_one({
        '_id': dashboard_id
    })
    # pylint: enable=protected-access
    if not dashboard:
        return return_error('Card doesn\'t exist')

    try:
        dashboard_metric = ChartMetrics[dashboard['metric']]
        handler_by_metric = {
            ChartMetrics.compare: fetch_chart_compare_historical,
            ChartMetrics.intersect: fetch_chart_intersect_historical,
            ChartMetrics.segment: fetch_chart_segment_historical,
            ChartMetrics.abstract: fetch_chart_abstract_historical
        }
        dashboard['data'] = handler_by_metric[dashboard_metric](dashboard, from_date, to_date)
        if dashboard['data'] is None:
            dashboard['data'] = []
            logger.error(f'Problematic queries in dashboard {dashboard}')
    except Exception:
        dashboard['data'] = []
        logger.exception(f'Problem handling dashboard {dashboard}')
    dashboard['space'] = str(dashboard['space'])
    return beautify_db_entry(dashboard)


@rev_cached(ttl=3600 * 24 * 365)
def generate_dashboard_historical(dashboard_id: ObjectId, from_date: datetime, to_date: datetime):
    return dashboard_historical_uncached(dashboard_id, from_date, to_date)
