from datetime import datetime
import pytest
from mongomock import ObjectId

from axonius.dashboard.chart.base import Chart
from axonius.entities import EntityType
from mocks.axonius_mock import AxoniusMock

# pylint: disable=redefined-outer-name


@pytest.fixture(scope='session', autouse=True)
def common():
    mock = AxoniusMock()
    mock.prepare_default()
    return mock


def test_chart_intersect(common):
    chart_id = common.insert_chart({
        'metric': 'intersect',
        'view': 'pie',
        'name': 'Intersection',
        'config': {
            'base': common.MANAGED_DEVICES_VIEW_ID,
            'base_color': '#D3D7DA',
            'entity': 'devices',
            'intersecting': [
                common.IPS_VIEW_ID,
                common.HOSTNAMES_VIEW_ID
            ],
            'intersecting_colors': []
        },
        'space': ObjectId('5f884545b3d8731c65f7be1a'),
        'user_id': ObjectId('5f884556625560e1f82fb802'),
        'last_updated': datetime.now()
    })
    chart_data = Chart.generate_from_id(chart_id, common)
    assert chart_data and len(chart_data) == 4, 'Unexpected data length'
    assert [d['value'] for d in chart_data] == [1, 1, 1, 1], 'Incorrect data values'
    common.update_chart(chart_id, {
        'config.base': common.WINDOWS_VIEW_ID
    })
    chart_data = Chart.generate_from_id(chart_id, common)
    assert chart_data and len(chart_data) == 4, 'Unexpected data length'
    assert [d['value'] for d in chart_data] == [1, 1, 1, 0], 'Incorrect data values'


def test_chart_compare(common):
    chart_id = common.insert_chart({
        'metric': 'compare',
        'view': 'histogram',
        'name': 'Compare',
        'config': {
            'views': [{
                'entity': 'devices',
                'id': common.MANAGED_DEVICES_VIEW_ID
            }, {
                'entity': 'devices',
                'id': common.WINDOWS_VIEW_ID
            }],
            'sort': {
                'sort_by': 'value',
                'sort_order': 'desc'
            }
        },
        'space': ObjectId('5f884545b3d8731c65f7be1a'),
        'user_id': ObjectId('5f884556625560e1f82fb802'),
        'last_updated': datetime.now()
    })
    chart_data = Chart.generate_from_id(chart_id, common)
    assert chart_data and len(chart_data) == 2, 'Unexpected data length'
    assert [d['value'] for d in chart_data] == [4, 3], 'Incorrect data values'


@pytest.mark.skip('Mongomock unsupporting')
def test_chart_segment(common):
    chart_id = common.insert_chart({
        'metric': 'segment',
        'view': 'histogram',
        'name': 'Segment',
        'config': {
            'entity': 'devices',
            'view': common.MANAGED_DEVICES_VIEW_ID,
            'field': {
                'filterable': True,
                'name': 'specific_data.data.hostname',
                'title': 'Host Name',
                'type': 'string'
            },
            'value_filter': [
                {
                    'name': '',
                    'value': ''
                }
            ],
            'sort': {
                'sort_by': 'value',
                'sort_order': 'desc'
            },
            'show_timeline': False,
            'timeframe': {
                'type': 'relative',
                'unit': 'day',
                'count': 7
            },
        },
        'space': ObjectId('5f884545b3d8731c65f7be1a'),
        'user_id': ObjectId('5f884556625560e1f82fb802'),
        'last_updated': datetime.now()
    })
    chart_data = Chart.generate_from_id(chart_id, common)
    assert chart_data and len(chart_data) == 4, 'Unexpected data length'
    assert [d['value'] for d in chart_data] == [1, 1, 1, 1], 'Incorrect data values'
    assert [d['name'] for d in chart_data] == common.HOST_NAMES, 'Incorrect data values'


def test_chart_segment_adapter(common):
    chart_id = common.insert_chart({
        'metric': 'adapter_segment',
        'view': 'adapter_histogram',
        'name': 'Adapter Segment',
        'config': {
            'entity': 'devices',
            'selected_view': common.WINDOWS_VIEW_ID,
            'sort': {
                'sort_by': 'value',
                'sort_order': 'desc'
            }
        },
        'space': ObjectId('5f884545b3d8731c65f7be1a'),
        'user_id': ObjectId('5f884556625560e1f82fb802'),
        'last_updated': datetime.now()
    })
    chart_data = Chart.generate_from_id(chart_id, common)
    assert chart_data and len(chart_data) == 1, 'Unexpected data length'
    assert [d['value'] for d in chart_data] == [3], 'Incorrect data values'


def test_chart_abstract(common):
    chart_id = common.insert_chart({
        'metric': 'abstract',
        'view': 'summary',
        'name': 'Abstract',
        'config': {
            'entity': 'devices',
            'view': common.WINDOWS_VIEW_ID,
            'field': {
                'filterable': True,
                'name': 'specific_data.data.number_of_processes',
                'title': 'Number Of Processes',
                'type': 'integer'
            },
            'func': 'count'
        },
        'space': ObjectId('5f884545b3d8731c65f7be1a'),
        'user_id': ObjectId('5f884556625560e1f82fb802'),
        'last_updated': datetime.now()
    })
    chart_data = Chart.generate_from_id(chart_id, common)
    assert chart_data and len(chart_data) == 1, 'Unexpected data length'
    assert chart_data[0]['value'] == 2, 'Incorrect data values'
    common.update_chart(chart_id, {
        'config.func': 'average'
    })
    chart_data = Chart.generate_from_id(chart_id, common)
    assert chart_data and len(chart_data) == 1, 'Unexpected data length'
    assert chart_data[0]['value'] == 3, 'Incorrect data values'


def test_chart_timeline(common):
    chart_id = common.insert_chart({
        'metric': 'timeline',
        'view': 'line',
        'name': 'Timeline',
        'config': {
            'views': [{
                'entity': 'devices',
                'id': common.MANAGED_DEVICES_VIEW_ID
            }, {
                'entity': 'devices',
                'id': common.WINDOWS_VIEW_ID
            }],
            'timeframe': {
                'type': 'relative',
                'unit': 'day',
                'count': 7
            },
            'intersection': False
        },
        'space': ObjectId('5f884545b3d8731c65f7be1a'),
        'user_id': ObjectId('5f884556625560e1f82fb802'),
        'last_updated': datetime.now()
    })
    chart_data = Chart.generate_from_id(chart_id, common)
    assert chart_data and len(chart_data) == 9, 'Unexpected data length'
    for (day, count_all, count_part) in chart_data[1:]:
        if not count_all:
            continue
        assert count_all - count_part in [0, 1]
        collection, query = common.data.entity_collection_query_for_date(EntityType.Devices, day.date().isoformat())
        assert collection.count_documents(query) == count_all


@pytest.mark.skip('Mongomock unsupporting')
def test_chart_timeline_segment(common):
    chart_id = common.insert_chart({
        'metric': 'segment_timeline',
        'view': 'line',
        'name': 'Timeline Segment',
        'config': {
            'entity': 'devices',
            'view': common.MANAGED_DEVICES_VIEW_ID,
            'field': {
                'filterable': True,
                'name': 'specific_data.data.hostname',
                'title': 'Host Name',
                'type': 'string'
            },
            'value_filter': [
                {
                    'name': '',
                    'value': ''
                }
            ],
            'timeframe': {
                'type': 'relative',
                'unit': 'day',
                'count': 7
            }
        },
        'space': ObjectId('5f884545b3d8731c65f7be1a'),
        'user_id': ObjectId('5f884556625560e1f82fb802'),
        'last_updated': datetime.now()
    })
    chart_data = Chart.generate_from_id(chart_id, common)
    assert chart_data and len(chart_data) == 9, 'Unexpected data length'


def test_chart_matrix(common):
    chart_id = common.insert_chart({
        'metric': 'matrix',
        'view': 'stacked',
        'name': 'Matrix',
        'config': {
            'entity': 'devices',
            'base': ['', common.MANAGED_DEVICES_VIEW_ID, common.WINDOWS_VIEW_ID],
            'intersecting': [common.RECENTLY_SEEN_VIEW_ID, common.IPS_VIEW_ID],
            'sort': {
                'sort_by': 'value',
                'sort_order': 'desc'
            }
        },
        'space': ObjectId('5f884545b3d8731c65f7be1a'),
        'user_id': ObjectId('5f884556625560e1f82fb802'),
        'last_updated': datetime.now()
    })
    chart_data = Chart.generate_from_id(chart_id, common)
    assert chart_data and len(chart_data) == 3, 'Unexpected data length'
