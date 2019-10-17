from datetime import datetime
from axonius.consts import plugin_consts
import uuid

from axonius.utils.hash import get_preferred_quick_adapter_id


def get_user_dict(test_name, user_id, plugin_name, plugin_unique_name):
    id_ = f'id_{test_name}_{user_id}'
    return {'accurate_for_datetime': datetime.now(),
            'adapters': [
                {'accurate_for_datetime': datetime.now(),
                 'client_used': f'client_{test_name}_{user_id}',
                 'quick_id': get_preferred_quick_adapter_id(plugin_unique_name, id_),
                 'data': {'id': id_,
                          'name': f'name_{test_name}_{user_id}',
                          'mail': f'name_{test_name}_{user_id}@organization.com',
                          'username': f'{test_name}_{user_id}',
                          'is_local': False,
                          'raw': {}},
                 'plugin_name': plugin_name,
                 'plugin_type': 'Adapter',
                 plugin_consts.PLUGIN_UNIQUE_NAME: plugin_unique_name}
    ],
        'internal_axon_id': uuid.uuid4().hex,
        'tags': []}
