import logging
from typing import List, Iterable, Tuple
from collections import defaultdict
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
from axonius.utils.gui_helpers import (find_filter_by_name, flatten_list, find_entity_field)
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
        #pylint: disable=protected-access
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


def _query_chart_segment_results(field: dict, view, entity: EntityType, for_date: datetime):
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

    field_name = field['name']
    adapter_conditions = [
        {
            '$ne': ['$$i.data._old', True]
        }
    ]

    if field_name.startswith(SPECIFIC_DATA):
        empty_field_name = field_name[len(SPECIFIC_DATA) + 1:]
        adapter_field_name = 'adapters.' + empty_field_name
        tags_field_name = 'tags.' + empty_field_name

    elif field_name.startswith(ADAPTERS_DATA):
        # e.g. adapters_data.aws_adapter.some_field
        splitted = field_name.split('.')
        adapter_data_adapter_name = splitted[1]

        # this condition is specific for fields that are in a specific adapter, so we
        # will not take other adapters that might share a field name (although the field itself might differ)
        adapter_conditions.append({
            '$eq': [f'$$i.{PLUGIN_NAME}', adapter_data_adapter_name]
        })
        empty_field_name = 'data.' + '.'.join(splitted[2:])
        adapter_field_name = 'adapters.' + empty_field_name
        tags_field_name = 'tags.' + empty_field_name

    return base_view, data_collection.aggregate([
        {
            '$match': base_query
        },
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
        {
            '$project': {
                'field': {
                    '$filter': {
                        'input': {
                            '$setUnion': [
                                '$' + adapter_field_name,
                                '$' + tags_field_name
                            ]
                        },
                        'as': 'i',
                        'cond': {
                            '$ne': ['$$i', []]
                        }
                    }
                }
            }
        },
        {
            '$group': {
                '_id': '$field',
                'value': {
                    '$sum': 1
                }
            }
        },
        {
            '$project': {
                'value': 1,
                'name': {
                    '$cond': {
                        'if': {
                            '$eq': [
                                '$_id', []
                            ]
                        },
                        'then': ['No Value'],
                        'else': '$_id'
                    }
                }
            }
        },
        {
            '$sort': {
                'value': -1
            }
        }
    ], allowDiskUse=True)


def fetch_chart_segment(chart_view: ChartViews, entity: EntityType, view, field, value_filter: str = '',
                        include_empty: bool = False, for_date=None) -> List:
    """
    Perform aggregation which matching given view's filter and grouping by give field, in order to get the
    number of results containing each available value of the field.
    For each such value, add filter combining the original filter with restriction of the field to this value.
    If the requested view is a pie, divide all found quantities by the total amount, to get proportions.

    :return: Data counting the amount / portion of occurrences for each value of given field, among the results
            of the given view's filter
    """
    # Query and data collections according to given module
    base_view, aggregate_results = _query_chart_segment_results(field, view, entity, for_date)
    if not base_view or not aggregate_results:
        return None
    base_filter = f'({base_view["query"]["filter"]}) and ' if base_view['query']['filter'] else ''
    data = []
    all_values = defaultdict(int)
    field_name = field['name']
    for item in aggregate_results:
        for value in set(flatten_list(item['name'])):
            all_values[value] += item['value']
    for field_value, field_count in all_values.items():
        query_filter = ''
        # Build the filter, according to the supported types
        if field_value == 'No Value':
            if not include_empty or value_filter:
                continue
            query_filter = f'not ({field_name} == exists(true))'
        elif isinstance(field_value, str):
            if value_filter.lower() not in field_value.lower():
                continue
            query_filter = f'{field_name} == "{field_value}"'
        elif isinstance(field_value, bool):
            query_filter = f'{field_name} == {str(field_value).lower()}'
        elif isinstance(field_value, int):
            query_filter = f'{field_name} == {field_value}'
        elif isinstance(field_value, datetime):
            query_filter = f'{field_name} == date("{field_value}")'

        data.append({
            'name': field_value,
            'value': field_count,
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

    dashboard_metric = ChartMetrics[dashboard['metric']]
    handler_by_metric = {
        ChartMetrics.compare: fetch_chart_compare,
        ChartMetrics.intersect: fetch_chart_intersect,
        ChartMetrics.segment: fetch_chart_segment,
        ChartMetrics.abstract: fetch_chart_abstract,
        ChartMetrics.timeline: fetch_chart_timeline
    }
    config = {**dashboard['config']}
    if config.get('entity') and ChartMetrics.compare != dashboard_metric:
        # _fetch_chart_compare crashed in the wild because it got entity as a param.
        # We don't understand how such a dashboard chart was created. But at lease we won't crash now
        config['entity'] = EntityType(dashboard['config']['entity'])
    try:
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
