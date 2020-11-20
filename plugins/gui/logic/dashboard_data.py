import logging
from collections import defaultdict
from bson import ObjectId

from axonius.consts.gui_consts import (ChartMetrics, SortType, SortOrder)
from axonius.consts.plugin_consts import PLUGIN_NAME
from axonius.dashboard.chart.base import Chart
from axonius.dashboard.chart.config import SortableConfig
from axonius.entities import EntityType
from axonius.modules.common import AxoniusCommon
from axonius.plugin_base import PluginBase, return_error
from axonius.utils.revving_cache import rev_cached, rev_cached_entity_type
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


def generate_dashboard_uncached(dashboard_id: ObjectId, sort_by=None, sort_order=None):
    """
    See _get_dashboard
    """
    common = AxoniusCommon()
    dashboard = common.data.find_chart(dashboard_id)
    if not dashboard:
        logger.error(f'Problem fetching dashboard to handle {dashboard_id}')
        return {}
    try:
        chart_obj = Chart.from_dict(dashboard)
        if sort_by and sort_order and isinstance(chart_obj.config, SortableConfig):
            chart_obj.config.apply_sort(sort_by, sort_order)
        dashboard['data'] = chart_obj.generate_data(common)

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
    common = AxoniusCommon()
    dashboard = common.data.find_chart(dashboard_id)
    if not dashboard:
        return return_error('Card doesn\'t exist')

    try:
        chart_obj = Chart.from_dict(dashboard)
        if chart_obj.metric == ChartMetrics.timeline:
            dashboard['error'] = 'Historical data generation for timeline chart is not supported'
            return beautify_db_entry(dashboard)
        if sort_by and sort_order and isinstance(chart_obj.config, SortableConfig):
            chart_obj.config.apply_sort(sort_by, sort_order)
        dashboard['data'] = chart_obj.generate_data(common, for_date)

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
