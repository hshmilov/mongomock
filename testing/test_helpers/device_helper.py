from datetime import datetime
from axonius.consts import plugin_consts
import uuid


def get_entity_adapter_dict(test_name, entity_adapter_id, plugin_name, plugin_unique_name, client_id=None):
    return {
        'accurate_for_datetime': datetime.now(),
        'client_used': client_id or f'client_{test_name}_{entity_adapter_id}',
        'data': {
            'id': f'id_{test_name}_{entity_adapter_id}',
            'name': f'name_{test_name}_{entity_adapter_id}',
            'os': {'bitness': None, 'distribution': '10', 'type': 'Windows'},
            'pretty_id': f'pretty_id_{test_name}_{entity_adapter_id}',
            'raw': {}
        },
        'plugin_name': plugin_name,
        'plugin_type': 'Adapter',
        plugin_consts.PLUGIN_UNIQUE_NAME: plugin_unique_name
    }


def get_entity_axonius_dict_multiadapter(test_name, list_of_adapter_data):
    return {
        'accurate_for_datetime': datetime.now(),
        'adapters': [
            get_entity_adapter_dict(test_name, *adapter_data)
            for adapter_data
            in list_of_adapter_data
        ],
        'internal_axon_id': uuid.uuid4().hex,
        'tags': []
    }


def get_entity_axonius_dict(test_name, entity_adapter_id, plugin_name, plugin_unique_name):
    return {
        'accurate_for_datetime': datetime.now(),
        'adapters': [
            get_entity_adapter_dict(test_name, entity_adapter_id, plugin_name, plugin_unique_name)
        ],
        'internal_axon_id': uuid.uuid4().hex,
        'tags': []
    }


def filter_by_plugin_name(devices, plugin_name):
    l = []
    for d in devices:
        if len([True for x in d.get('adapters', []) if x == plugin_name]) > 0:
            l.append(d)
    return l
