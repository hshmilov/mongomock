# pylint: disable=too-many-lines
import logging
from collections import defaultdict, Counter, Hashable
from datetime import date, datetime, timedelta
from multiprocessing import cpu_count
from typing import (List, Iterable, Tuple, Optional)
import re

from bson import ObjectId
from dateutil.parser import parse as parse_date

from axonius.consts.adapter_consts import PREFERRED_FIELDS_PREFIX
from axonius.consts.gui_consts import (ChartMetrics, ChartViews, ChartFuncs, ChartRangeTypes, ChartRangeUnits,
                                       ADAPTERS_DATA, SPECIFIC_DATA, RANGE_UNIT_DAYS,
                                       DASHBOARD_COLLECTION, SortType, SortOrder, LABELS_FIELD)
from axonius.consts.plugin_consts import PLUGIN_NAME
from axonius.entities import EntityType
from axonius.modules.query.axonius_query import get_axonius_query_singleton
from axonius.plugin_base import PluginBase, return_error
from axonius.utils.axonius_query_language import (convert_db_entity_to_view_entity)
from axonius.utils.gui_helpers import (find_entity_field, get_string_from_field_value, get_adapters_metadata)
from axonius.utils.revving_cache import rev_cached, rev_cached_entity_type
from axonius.utils.threading import GLOBAL_RUN_AND_FORGET
from gui.logic.db_helpers import beautify_db_entry

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
    aggregate_query = [{'$group': {'_id': f'$adapters.{PLUGIN_NAME}', 'count': {'$sum': 1}}}]
    total = 0
    for res in entity_collection.aggregate(aggregate_query):
        for plugin_name in set(res['_id']):
            entities_per_adapters[plugin_name]['value'] += res['count']
            total += res['count']
            adapter_entities['seen'] += res['count']

        for plugin_name in res['_id']:
            entities_per_adapters[plugin_name]['meta'] += res['count']
            adapter_entities['seen_gross'] += res['count']
    for name, value in entities_per_adapters.items():
        adapter_entities['counters'].append({
            'name': name, 'portion': value['value'] / total, **value
        })

    return adapter_entities


def fetch_chart_compare(chart_view: ChartViews, views: List, sort,
                        selected_sort_by=None, selected_sort_order=None, for_date: str = None) -> List:
    """
    Iterate given views, fetch each one's filter from the appropriate query collection, according to its module,
    and execute the filter on the appropriate entity collection.

    :param chart_view:
    :param views: List of views to fetch data by for comparing results
    :param sort default chart sort in db
    :param selected_sort_by selected sort type in ui session
    :param selected_sort_order selected sort order asc/desc in ui session
    :return:
    """
    if not views:
        raise Exception('No views for the chart')

    axonius_query = get_axonius_query_singleton()
    data = []
    total = 0
    # for view in views:
    for i, _ in enumerate(views):
        # Can be optimized by taking all names in advance and querying each module's collection once
        # But since list is very short the simpler and more readable implementation is fine
        entity_name = _.get('entity', EntityType.Devices.value)
        entity = EntityType(entity_name)
        view_dict = axonius_query.data.find_view(entity, _['id'])
        if not view_dict:
            continue

        data_item_color = _.get('chart_color', None)

        data_item = {
            'view_id': _['id'],
            'name': view_dict['name'],
            'view': view_dict['view'],
            'module': entity_name,
            'value': 0,
            'chart_color': data_item_color,
            'index_in_config': i
        }
        entity_collection, date_query = axonius_query.data.entity_collection_query_for_date(entity, for_date)
        query_filter = [date_query] if date_query else []
        query_filter.append(axonius_query.parse_aql_filter_for_day(view_dict['view']['query']['filter'],
                                                                   for_date, entity))
        data_item['value'] = axonius_query.count_matches(entity_collection, {
            '$and': query_filter
        })
        data.append(data_item)
        total += data_item['value']

    data = _sort_dashboard_data(data, selected_sort_by, selected_sort_order, sort)
    if chart_view == ChartViews.pie and not total:
        return []
    return [{**x, 'portion': (x['value'] / total if total else 0)} for x in data]

# pylint: disable=R0914


# pylint: disable=too-many-branches,too-many-statements
def fetch_chart_intersect(
        _: ChartViews,
        entity: EntityType,
        base, intersecting,
        base_color=None,
        intersecting_colors=None,
        for_date: str = None) -> Optional[List]:
    """
    This chart shows intersection of 1 or 2 'Child' views with a 'Parent' (expected not to be a subset of them).
    Module to be queried is defined by the parent query.

    :param _: Placeholder to create uniform interface for the chart fetching methods
    :param entity:
    :param base:
    :param intersecting: List of 1 or 2 views
    :param base_color: The base query color
    :param intersecting_colors: The intersecting queries colors
    :param for_date: Data will be fetched and calculated according to what is stored on this for_date
    :return: List of result portions for the query executions along with their names. First represents Parent query.
             If 1 child, second represents Child intersecting with Parent.
             If 2 children, intersection between all three is calculated, namely 'Intersection'.
                            Second and third represent each Child intersecting with Parent, excluding Intersection.
                            Fourth represents Intersection.
    """
    if not intersecting or len(intersecting) < 1:
        raise Exception('Pie chart requires at least one views')
    axonius_query = get_axonius_query_singleton()
    data_collection, date_query = axonius_query.data.entity_collection_query_for_date(entity, for_date)

    base_view = {'query': {'filter': '', 'expressions': []}}
    base_queries = [date_query] if date_query else []
    base_name = 'ALL'
    if base:
        base_from_db = axonius_query.data.find_view(entity, base)
        if not base_from_db or not base_from_db.get('view', {}).get('query'):
            return None
        base_view = base_from_db['view']
        base_name = base_from_db.get('name', '')
        base_queries.append(axonius_query.parse_aql_filter_for_day(base_view['query']['filter'], for_date, entity))

    data = []
    total = axonius_query.count_matches(data_collection, {'$and': base_queries} if base_queries else {})
    if not total:
        return [{
            'name': base_name,
            'value': 0,
            'portion': 0,
            'remainder': True,
            'view': {**base_view, 'query': {'filter': base_view['query']['filter']}},
            'module': entity.value,
            'index_in_config': 0
        }]

    child1_from_db = axonius_query.data.find_view(entity, intersecting[0])
    if not child1_from_db or not child1_from_db.get('view', {}).get('query'):
        return None
    child1_view = child1_from_db['view']
    child1_name = child1_from_db.get('name', '')
    child1_filter = child1_view['query']['filter']
    child1_query = axonius_query.parse_aql_filter_for_day(child1_filter, for_date, entity)
    base_filter = f'({base_view["query"]["filter"]}) and ' if base_view['query']['filter'] else ''
    child2_filter = ''
    if len(intersecting) == 1:
        # Fetch the only child, intersecting with parent
        child1_view['query']['filter'] = f'{base_filter}({child1_filter})'
        numeric_value = axonius_query.count_matches(data_collection, {
            '$and': base_queries + [child1_query]
        })
        data.append({
            'name': child1_name,
            'view': child1_view,
            'module': entity.value,
            'value': numeric_value,
            'portion': numeric_value / total,
            'index_in_config': 1
        })
    else:
        child2_from_db = axonius_query.data.find_view(entity, intersecting[1])
        if not child2_from_db or not child2_from_db.get('view', {}).get('query'):
            return None
        child2_view = child2_from_db['view']
        child2_name = child2_from_db.get('name', '')
        child2_filter = child2_view['query']['filter']
        child2_query = axonius_query.parse_aql_filter_for_day(child2_filter, for_date, entity)

        # Child1 + Parent - Intersection
        child1_view['query']['filter'] = f'{base_filter}({child1_filter}) and not ({child2_filter})'
        numeric_value = axonius_query.count_matches(data_collection, {
            '$and': base_queries + [
                child1_query,
                {
                    '$nor': [child2_query]
                }
            ]
        })
        data.append({
            'name': child1_name,
            'value': numeric_value,
            'portion': numeric_value / total,
            'module': entity.value,
            'view': child1_view,
            'index_in_config': 1
        })

        # Intersection
        numeric_value = axonius_query.count_matches(data_collection, {
            '$and': base_queries + [
                child1_query, child2_query
            ]
        })
        data.append({
            'name': f'{child1_name} + {child2_name}',
            'intersection': True,
            'value': numeric_value,
            'portion': numeric_value / total,
            'view': {**base_view, 'query': {'filter': f'{base_filter}({child1_filter}) and ({child2_filter})'}},
            'module': entity.value
        })

        # Child2 + Parent - Intersection
        child2_view['query']['filter'] = f'{base_filter}({child2_filter}) and not ({child1_filter})'
        numeric_value = axonius_query.count_matches(data_collection, {
            '$and': base_queries + [
                child2_query,
                {
                    '$nor': [child1_query]
                }
            ]
        })
        data.append({
            'name': child2_name,
            'value': numeric_value,
            'portion': numeric_value / total,
            'module': entity.value,
            'view': child2_view,
            'index_in_config': 2
        })

    remainder = 1 - sum([x['portion'] for x in data])
    numeric_remainder = total - sum([x['value'] for x in data])
    child2_or = f' or ({child2_filter})' if child2_filter else ''
    return [{
        'name': base_name,
        'portion': remainder,
        'value': numeric_remainder,
        'remainder': True,
        'view': {
            **base_view, 'query': {'filter': f'{base_filter}not (({child1_filter}){child2_or})'}
        },
        'module': entity.value,
        'index_in_config': 0
    }, *data]


# pylint: disable-msg=too-many-locals
def _query_chart_segment_results(field_parent: str, view, entity: EntityType, for_date: str,
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
    axonius_query = get_axonius_query_singleton()
    base_view = {'query': {'filter': '', 'expressions': []}}
    data_collection, date_query = axonius_query.data.entity_collection_query_for_date(entity, for_date)
    base_queries = [date_query] if date_query else []
    if view:
        base_filter = axonius_query.data.find_view_filter(entity, view)
        if not base_filter:
            return None, None
        base_queries.append(axonius_query.parse_aql_filter_for_day(base_filter, for_date, entity))

    base_query = {'$and': base_queries} if base_queries else {}
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
            '$match': axonius_query.convert_for_aggregation_matches(data_collection, base_query)
        },
        # filter old data from adapters
        {
            '$project': {
                'tags': {
                    '$filter': {
                        'input': '$tags',
                        'as': 'i',
                        'cond': {
                            '$eq': ['$$i.type', 'adapterdata']
                        }
                    }
                } if LABELS_FIELD not in filters_keys else {'$map': {
                    'input': '$labels',
                    'as': 'l',
                    'in': {
                        'name': '$$l'
                    }
                }},
                'adapters': {
                    '$filter': {
                        'input': '$adapters',
                        'as': 'i',
                        'cond': {
                            '$and': adapter_conditions
                        }
                    }
                },
                PREFERRED_FIELDS_PREFIX: 1
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
# pylint: disable=too-many-arguments
def fetch_chart_segment(chart_view: ChartViews, entity: EntityType, view, field, sort, value_filter: list = None,
                        include_empty: bool = False, for_date: str = None,
                        selected_sort_by=None, selected_sort_order=None, timeframe=None, show_timeline=None,
                        chart_color=None) -> List:
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
    reduced_filters = _get_reduced_filters(field_name, value_filter)

    # Query and data collections according to given module
    base_view, aggregate_results = _query_chart_segment_results(field_parent, view, entity, for_date,
                                                                filters_keys=[*reduced_filters])
    if not base_view or not aggregate_results:
        return None

    base_filter = f'({base_view["query"]["filter"]}) and ' if base_view['query']['filter'] else ''
    counted_results = _get_counted_results(aggregate_results, reduced_filters)
    data = []
    for result_name, result_count in counted_results.items():
        if result_name == 'No Value':
            if not include_empty or ''.join(reduced_filters[field_name]):
                continue
            query_filter = f'not ({field_parent}.{field_name} == exists(true))' if not field_name == LABELS_FIELD else \
                f'not ({field_name} == exists(true))'
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

    data = _sort_dashboard_data(data, selected_sort_by, selected_sort_order, sort)
    total = sum([x['value'] for x in data])
    return [{**x, 'portion': x['value'] / total} for x in data]


def _get_counted_results(aggregate_results, reduced_filters):
    counted_results = Counter()
    for item in aggregate_results:
        extra_data = item.get('extra_data', [])
        if 'No Value' in extra_data:
            counted_results['No Value'] += 1
        elif _match_result_item_to_filters(extra_data, reduced_filters):
            result_name = item.get('_id', {}).get('name', 'No Value')
            if not isinstance(result_name, Hashable):
                continue
            counted_results[result_name] += 1
    return counted_results


def _get_reduced_filters(field_name, value_filter):
    if not value_filter:
        value_filter = []
    # backward compatibility: old filters used to be strings
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
    return reduced_filters


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

    def escape_regex_value(_value):
        return re.escape(_value)

    def escape_new_line(_value):
        return _value.replace('\n', '\\n')

    query_filter = ''
    if isinstance(value, str):
        if value in ['false', 'true']:
            query_filter = f'{field_name} == {value}'
        else:
            if with_regex:
                query_filter = f'{field_name} == regex("{escape_regex_value(value)}","i")'
            else:
                query_filter = f'{field_name} == "{escape_new_line(value)}"'
    elif isinstance(value, (int, float)):
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
    if field_key == LABELS_FIELD:
        field_key = 'name'
    field_prefix = ''.join(field_adapter_parent.split('.')[2:])
    return {
        '$reduce': {
            'input': {
                '$setUnion': [
                    f'{field_adapter_parent}',
                    f'{field_tags_parent}',
                    [f'$preferred_fields.{field_prefix}' if field_prefix else '$preferred_fields']
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


def _query_chart_abstract_results(field: dict, entity: EntityType, view_from_db, for_date: str):
    """
    Build the query and retrieve data for calculating the abstract chart for given field and view
    """
    axonius_query = get_axonius_query_singleton()
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
        logger.info(f'Chart defined with unsupported field {field["name"]}')
        return None, None

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
    data_collection, date_query = axonius_query.data.entity_collection_query_for_date(entity, for_date)
    if date_query:
        base_query = {'$and': [base_query, date_query]}

    if view_from_db:
        base_view = view_from_db['view']
        if not base_view or not base_view.get('query'):
            return None, None
        base_query = {
            '$and': [
                axonius_query.parse_aql_filter_for_day(base_view['query']['filter'], for_date, entity),
                base_query
            ]
        }
        base_view['query']['filter'] = f'({base_view["query"]["filter"]}) and '

    field_compare = 'true' if field['type'] == 'bool' else 'exists(true)'
    if field['type'] in ['number', 'integer']:
        field_compare = f'{field_compare} and {field["name"]} > 0'
    base_view['query']['filter'] = f'{base_view["query"]["filter"]}{field["name"]} == {field_compare}'

    # pylint: enable=protected-access
    return base_view, data_collection.find(base_query, projection={
        adapter_field_name: 1,
        tags_field_name: 1,
        f'adapters.{PLUGIN_NAME}': 1,
        f'tags.{PLUGIN_NAME}': 1
    })


def fetch_chart_abstract(_: ChartViews, entity: EntityType, view, field, func, for_date: str = None):
    """
    One piece of data summarizing the given field's values resulting from given view's query, according to given func
    """
    # Query and data collections according to given module

    field_name = field['name']
    view_from_db = get_axonius_query_singleton().data.find_view(entity, view) if view else None
    base_view, results = _query_chart_abstract_results(field, entity, view_from_db, for_date)
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

    view_name = view_from_db['name'] if view else 'ALL'
    if not count:
        return [{'name': view_name, 'value': 0, 'view': base_view, 'module': entity.value}]
    name = f'{func} of {field["title"]} on {view_name} results'
    if ChartFuncs[func] == ChartFuncs.average:
        return [{
            'name': name, 'value': (sigma / count), 'schema': field, 'view': base_view, 'module': entity.value
        }]
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
    return date_from.replace(tzinfo=None), date_to.replace(tzinfo=None)


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
    axonius_query = get_axonius_query_singleton()
    for view in views:
        if not view.get('id'):
            continue
        entity = EntityType(view['entity'])
        base_from_db = axonius_query.data.find_view(entity, view['id'])
        base_view = base_from_db['view']
        if not base_view or not base_view.get('query'):
            return
        yield {
            'title': base_from_db['name'],
            'points': _fetch_timeline_points(entity, base_view['query']['filter'], date_ranges)
        }


def _intersect_timeline_lines(views, date_ranges):
    axonius_query = get_axonius_query_singleton()
    if len(views) != 2 or not views[0].get('id'):
        logger.error(f'Unexpected number of views for performing intersection {len(views)}')
        return
    first_entity_type = EntityType(views[0]['entity'])
    second_entity_type = EntityType(views[1]['entity'])

    # first query handling
    base_filter = ''
    if views[0].get('id'):
        base_from_db = axonius_query.data.find_view(first_entity_type, views[0]['id'])
        base_view = base_from_db['view']
        if not base_view or not base_view.get('query'):
            return
        base_filter = base_view['query']['filter']
    yield {
        'title': base_from_db['name'],
        'points': _fetch_timeline_points(first_entity_type, base_filter, date_ranges)
    }

    # second query handling
    intersecting_from_db = axonius_query.data.find_view(second_entity_type, views[1]['id'])
    if not intersecting_from_db or not intersecting_from_db.get('view', {}).get('query'):
        return
    intersecting_view = intersecting_from_db['view']
    intersecting_filter = intersecting_view.get('query', {}).get('filter', '')
    if base_filter:
        intersecting_filter = f'({base_filter}) and {intersecting_filter}'
    yield {
        'title': f'{base_from_db["name"]} and {intersecting_from_db["name"]}',
        'points': _fetch_timeline_points(second_entity_type, intersecting_filter, date_ranges)
    }


def fetch_timeline_points_for_segmentation(entity_type: EntityType, match_filter: str, date_ranges):
    axonius_query = get_axonius_query_singleton()

    def aggregate_for_date_range(args):
        range_from, range_to = args
        historical_collection = axonius_query.data.entity_history_collection[entity_type]
        historical_in_range = historical_collection.aggregate([{
            '$project': {
                'accurate_for_datetime': 1
            }
        }, {
            '$match': {
                'accurate_for_datetime': {
                    '$lte': datetime.combine(range_to, datetime.min.time()),
                    '$gte': datetime.combine(range_from, datetime.min.time()),
                }
            }
        }, {
            '$group': {
                '_id': '$accurate_for_datetime'
            }
        }])

        return [historical_group['_id'] for historical_group in historical_in_range]
    full_dates = []
    for results in list(GLOBAL_RUN_AND_FORGET.map(aggregate_for_date_range, date_ranges)):
        for accurate_for_datetime in results:
            full_dates.append({
                'date': accurate_for_datetime.strftime('%m/%d/%Y'),
                'full_date': accurate_for_datetime
            })
    return full_dates


def _fetch_timeline_points(entity_type: EntityType, match_filter: str, date_ranges):
    axonius_query = get_axonius_query_singleton()

    def aggregate_for_date_range(args):
        range_from, range_to = args
        historical_collection = axonius_query.data.entity_history_collection[entity_type]
        historical_in_range = historical_collection.aggregate([{
            '$project': {
                'accurate_for_datetime': 1
            }
        }, {
            '$match': {
                'accurate_for_datetime': {
                    '$lte': datetime.combine(range_to, datetime.min.time()),
                    '$gte': datetime.combine(range_from, datetime.min.time()),
                }
            }
        }, {
            '$group': {
                '_id': '$accurate_for_datetime'
            }
        }])

        historical_counts = {}
        for historical_group in historical_in_range:
            group_date = historical_group['_id']
            collection, date_query = axonius_query.data.entity_collection_query_for_date(
                entity_type, group_date.strftime('%Y-%m-%d'))
            base_filter = axonius_query.parse_aql_filter(match_filter, group_date, entity_type)
            if date_query:
                base_filter = {
                    '$and': [base_filter, date_query]
                }
            historical_counts[group_date] = axonius_query.count_matches(collection, base_filter)
        return historical_counts
    # pylint: enable=protected-access
    points = {}
    for results in list(GLOBAL_RUN_AND_FORGET.map(aggregate_for_date_range, date_ranges)):
        for accurate_for_datetime, count in results.items():
            points[accurate_for_datetime.strftime('%m/%d/%Y')] = count
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
    return _format_timeline_chart(date_from, date_to, lines)


def fetch_chart_segment_timeline(_: ChartViews, entity: EntityType, view, field,
                                 include_empty: bool = False, value_filter: list = None, timeframe=None):
    date_from, date_to = _parse_range_timeline(timeframe)
    if not date_from or not date_to:
        return None
    date_ranges = list(_get_date_ranges(date_from, date_to))
    date_points = fetch_timeline_points_for_segmentation(EntityType(entity), '', date_ranges)

    field_name_partition = field['name'].rpartition('.')
    field_parent = field_name_partition[0] or ''
    field_name = field_name_partition[2]
    reduced_filters = _get_reduced_filters(field_name, value_filter)

    lines = [{'title': 'Segment count', 'points': {}}, {'title': 'Total segment values', 'points': {}}]
    for curr_point in date_points:
        base_view, aggregate_results = _query_chart_segment_results(field_parent, view, entity,
                                                                    curr_point['full_date'],
                                                                    filters_keys=[*reduced_filters])
        if not base_view or not aggregate_results:
            continue

        # go over segmentation results
        counted_results = _get_counted_results(aggregate_results, reduced_filters)
        total_count = 0
        num_of_segments = 0
        for result_name, result_count in counted_results.items():
            if result_name == 'No Value':
                if not include_empty or ''.join(reduced_filters[field_name]):
                    continue
            num_of_segments += 1
            total_count += result_count
        # number of segments for this date
        lines[0]['points'][curr_point['date']] = num_of_segments
        # total values of all segments for this date
        lines[1]['points'][curr_point['date']] = total_count

    return _format_timeline_chart(date_from, date_to, lines)


def _format_timeline_chart(date_from, date_to, lines):
    if not lines or not lines[0].keys():
        return None
    # find the first date with value
    # before this date data is not relevant
    first_date_with_value = datetime.strptime(min([min(line_group['points'].keys()) for line_group in lines]),
                                              '%m/%d/%Y')
    # fix the from_date for not having undefined values before the first day we have values
    if date_from < first_date_with_value:
        date_from = first_date_with_value

    scale = [(date_from + timedelta(i)) for i in range((date_to - date_from).days + 1)]
    return [
        ['Day'] + [{
            'label': line['title'],
            'type': 'number'
        } for line in lines],
        *[[day] + [line['points'].get(day.strftime('%m/%d/%Y')) for line in lines] for day in scale]
    ]


def fetch_chart_matrix(
        _: ChartViews,
        entity: EntityType,
        base, intersecting,
        sort,
        selected_sort_by=None,
        selected_sort_order=None,
        intersecting_colors=None,
        for_date: str = None) -> Optional[List]:
    axonius_query = get_axonius_query_singleton()
    # Query and data collections according to given parent's module
    data_collection, date_query = axonius_query.data.entity_collection_query_for_date(entity, for_date)

    # go over base queries
    data = []
    has_results = False
    total_values = defaultdict(int)
    for base_query_index, base_query_id in enumerate(base):
        base_view = {'query': {'filter': '', 'expressions': []}}
        if base_query_id:
            base_from_db = axonius_query.data.find_view(entity, base_query_id)
            base_query_name = base_from_db['name']
            base_view = base_from_db['view']
            if not base_view.get('query'):
                continue
        else:
            base_query_name = f'All {entity.value}'

        base_queries = [date_query] if date_query else []
        base_queries.append(axonius_query.parse_aql_filter_for_day(base_view['query']['filter'], for_date, entity))
        base_filter = f'({base_view["query"]["filter"]}) and ' if base_view['query']['filter'] else ''

        # intersection of base query with each data query
        for intersecting_query_index, intersecting_query_id in enumerate(intersecting):
            child_from_db = axonius_query.data.find_view(entity, intersecting_query_id)
            intersecting_query_name = child_from_db['name']
            child_view = child_from_db['view']

            if not child_view or not child_view.get('query'):
                continue
            child_filter = child_view['query']['filter']
            child_query = axonius_query.parse_aql_filter_for_day(child_filter, for_date, entity)
            child_view['query']['filter'] = f'{base_filter}({child_filter})'
            child_view['query']['expressions'] = []
            numeric_value = data_collection.count_documents({
                '$and': base_queries + [child_query]
            })

            if numeric_value != 0:
                has_results = True

            total_values[base_query_index] += numeric_value

            data.append({'intersectionName': intersecting_query_name,
                         'intersectionIndex': intersecting_query_index,
                         'name': base_query_name,
                         'baseIndex': base_query_index,  # used to distinguish between base queries with same name
                         'view': child_view,
                         'module': entity.value,
                         'numericValue': numeric_value})

    # no intersections found - return an empty response
    if not has_results:
        return None

    total = sum(total_values.values())
    intersected_data = {}

    for data_entry in data:
        data_entry['value'] = total_values[data_entry['baseIndex']]
        data_entry['portion'] = data_entry['value'] / total

        index = data.index(data_entry)
        if not data_entry.get('numericValue'):
            continue

        current_base_query_index = data_entry.get('baseIndex')
        if not intersected_data.get(current_base_query_index):
            intersected_data[current_base_query_index] = {
                'name': data_entry.get('name'),
                'intersections': [],
                'value': data_entry.get('value')
            }
        intersected_data[current_base_query_index].get('intersections').append({
            'name': data_entry.get('intersectionName'),
            'intersectionIndex': data_entry.get('intersectionIndex'),
            'value': data_entry.get('numericValue'),
            'view': data_entry.get('view'),
            'module': data_entry.get('module'),
            'originalIndex': index,
        })

    return _sort_dashboard_data(intersected_data.values(), selected_sort_by, selected_sort_order, sort)


def fetch_chart_adapter_segment(chart_view: ChartViews, entity: EntityType, selected_view, sort,
                                selected_sort_by=None, selected_sort_order=None, for_date: str = None,
                                chart_colors=None):
    axonius_query = get_axonius_query_singleton()
    data_collection, date_query = axonius_query.data.entity_collection_query_for_date(entity, for_date)
    adapters_metadata = get_adapters_metadata()

    view_query_config = {'query': {'filter': '', 'expressions': []}}
    base_queries = [date_query] if date_query else []
    if selected_view:
        view = axonius_query.data.find_view(entity, selected_view) or {}
        view_query_config = view.get('view')
        if not view_query_config or not view_query_config.get('query'):
            return None
        base_queries.append(axonius_query.parse_aql_filter_for_day(view_query_config['query']['filter'],
                                                                   for_date, entity))

    condition = {'$and': base_queries} if base_queries else {}
    matching_devices = data_collection.find(condition, {'adapters.plugin_name': 1})

    total_count = matching_devices.count()
    if total_count == 0:
        return None

    count_per_adapter = defaultdict(int)
    for device_adapters in matching_devices:
        adapter_names = {adapter['plugin_name'] for adapter in device_adapters['adapters']}
        for adapter_name in adapter_names:
            count_per_adapter[adapter_name] += 1

    data = []
    query_filter = view_query_config['query']['filter']
    for adapter_name in count_per_adapter.keys():
        adapter_view = {'query': {}, 'expressions': []}
        adapter_filter = f'(adapters == \"{adapter_name}\")'
        if not query_filter:
            adapter_view['query']['filter'] = adapter_filter
        else:
            adapter_view['query']['filter'] = f'({query_filter}) and {adapter_filter}'
        data.append({
            'name': adapter_name,
            'fullName': adapters_metadata[adapter_name]['title'],
            'value': count_per_adapter[adapter_name],
            'portion': count_per_adapter[adapter_name] / total_count,
            'uniqueDevices': total_count,
            'module': entity.value,
            'view': adapter_view
        })
    # when sorting by name use adapter title
    data = _sort_dashboard_data(data, selected_sort_by, selected_sort_order, sort, name_field='fullName')
    return data


def generate_dashboard_uncached(dashboard_id: ObjectId, sort_by=None, sort_order=None):
    """
    See _get_dashboard
    """
    # pylint: disable=protected-access
    dashboard = PluginBase.Instance._get_collection(DASHBOARD_COLLECTION).find_one({
        '_id': dashboard_id
    })
    if not dashboard:
        logger.error(f'Problem fetching dashboard to handle {dashboard_id}')
        return {}

    # pylint: enable=protected-access
    handler_by_metric = {
        ChartMetrics.compare: fetch_chart_compare,
        ChartMetrics.intersect: fetch_chart_intersect,
        ChartMetrics.segment: fetch_chart_segment,
        ChartMetrics.segment_timeline: fetch_chart_segment_timeline,
        ChartMetrics.adapter_segment: fetch_chart_adapter_segment,
        ChartMetrics.abstract: fetch_chart_abstract,
        ChartMetrics.timeline: fetch_chart_timeline,
        ChartMetrics.matrix: fetch_chart_matrix
    }
    config = {**dashboard['config']}

    def call_dashboard_handler(metric):
        if metric in [ChartMetrics.segment, ChartMetrics.compare, ChartMetrics.matrix, ChartMetrics.adapter_segment]:
            return handler_by_metric[metric](ChartViews[dashboard['view']],
                                             selected_sort_by=sort_by,
                                             selected_sort_order=sort_order,
                                             **config)
        return handler_by_metric[metric](ChartViews[dashboard['view']], **config)

    try:
        dashboard_metric = ChartMetrics[dashboard['metric']]
        if config.get('entity') and ChartMetrics.compare != dashboard_metric:
            # _fetch_chart_compare crashed in the wild because it got entity as a param.
            # We don't understand how such a dashboard chart was created. But at least we won't crash now
            config['entity'] = EntityType(dashboard['config']['entity'])
        dashboard['data'] = call_dashboard_handler(dashboard_metric)
        if dashboard['data'] is None:
            dashboard['data'] = []
            logger.error(f'Problematic queries in dashboard {dashboard}')
    except Exception:
        dashboard['data'] = []
        logger.exception(f'Problem handling dashboard {dashboard}')
    dashboard['space'] = str(dashboard['space'])
    return beautify_db_entry(dashboard)


# there's no trivial way to remove the TTL functionality entirely, so let's just make it long enough
@rev_cached(ttl=3600 * 6, blocking=False)
def generate_dashboard(dashboard_id: ObjectId, sort_by=None, sort_order=None):
    return generate_dashboard_uncached(dashboard_id, sort_by, sort_order)


def dashboard_historical_uncached(dashboard_id: ObjectId, for_date: str, sort_by=None, sort_order=None):
    # pylint: disable=protected-access
    dashboard = PluginBase.Instance._get_collection(DASHBOARD_COLLECTION).find_one({
        '_id': dashboard_id
    })
    # pylint: enable=protected-access
    if not dashboard:
        return return_error('Card doesn\'t exist')

    try:
        dashboard_metric = ChartMetrics[dashboard['metric']]

        if dashboard_metric == ChartMetrics.timeline:
            dashboard['error'] = 'Historical data generation for timeline chart is not supported'
            return beautify_db_entry(dashboard)

        handler_by_metric = {
            ChartMetrics.compare: fetch_chart_compare,
            ChartMetrics.intersect: fetch_chart_intersect,
            ChartMetrics.segment: fetch_chart_segment,
            ChartMetrics.adapter_segment: fetch_chart_adapter_segment,
            ChartMetrics.abstract: fetch_chart_abstract,
            ChartMetrics.matrix: fetch_chart_matrix
        }
        config = {**dashboard['config']}

        def call_dashboard_handler(metric):
            if metric in [ChartMetrics.segment, ChartMetrics.compare]:
                return handler_by_metric[dashboard_metric](dashboard,
                                                           selected_sort_by=sort_by,
                                                           selected_sort_order=sort_order,
                                                           **config,
                                                           for_date=for_date)
            return handler_by_metric[dashboard_metric](dashboard, **config, for_date=for_date)

        if config.get('entity') and ChartMetrics.compare != dashboard_metric:
            # _fetch_chart_compare crashed in the wild because it got entity as a param.
            # We don't understand how such a dashboard chart was created. But at least we won't crash now
            config['entity'] = EntityType(dashboard['config']['entity'])
        dashboard['data'] = call_dashboard_handler(dashboard_metric)
        if dashboard['data'] is None:
            dashboard['data'] = []
            logger.error(f'Problematic queries in dashboard {dashboard}')
    except Exception:
        dashboard['data'] = []
        logger.exception(f'Problem handling dashboard {dashboard}')
    dashboard['space'] = str(dashboard['space'])
    return beautify_db_entry(dashboard)


@rev_cached(ttl=3600 * 24 * 365)
def generate_dashboard_historical(dashboard_id: ObjectId, for_date: str, sort_by=None, sort_order=None):
    return dashboard_historical_uncached(dashboard_id, for_date, sort_by, sort_order)


def _sort_dashboard_data(data, selected_sort_by, selected_sort_order, default_chart_sort,
                         value_field='value', name_field='name'):
    # If nothing received from client, get the default sorting from chart config, If exists.
    sort_by = selected_sort_by or (default_chart_sort.get('sort_by', SortType.VALUE.value)
                                   if default_chart_sort else SortType.VALUE.value)
    sort_order = selected_sort_order or (default_chart_sort.get('sort_order', SortOrder.DESC.value)
                                         if default_chart_sort else SortOrder.DESC.value)
    should_reverse = sort_order == SortOrder.DESC.value

    return sorted(data, key=lambda x: (x[value_field], str(x[name_field]).upper()), reverse=should_reverse) \
        if sort_by == SortType.VALUE.value \
        else sorted(data, key=lambda x: str(x[name_field]).upper(), reverse=should_reverse)


def is_dashboard_paginated(generated_dashboard):
    metric = generated_dashboard.get('metric')
    if metric:
        return ChartMetrics[metric] != ChartMetrics.timeline
    return True
