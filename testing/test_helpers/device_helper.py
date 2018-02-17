from datetime import datetime
from axonius.consts import plugin_consts
import uuid


def get_device_dict(test_name, device_id, plugin_name, plugin_unique_name):
    return {'accurate_for_datetime': datetime.now(),
            'adapters': [
                {'accurate_for_datetime': datetime.now(),
                 'client_used': f'client_{test_name}_{device_id}',
                 'data': {'id': f'id_{test_name}_{device_id}',
                          'name': f'name_{test_name}_{device_id}',
                          'os': {'bitness': None, 'distribution': '10', 'type': 'Windows'},
                          'pretty_id': f'pretty_id_{test_name}_{device_id}',
                          'raw': {}},
                 'plugin_name': plugin_name,
                 'plugin_type': 'Adapter',
                 plugin_consts.PLUGIN_UNIQUE_NAME: plugin_unique_name}
    ],
        'internal_axon_id': uuid.uuid4().hex,
        'tags': []}


def filter_by_plugin_name(devices, plugin_name):
    l = []
    for d in devices:
        if len([True for x in d.get('adapters', []) if x == plugin_name]) > 0:
            l.append(d)
    return l
