import copy

DEFAULT_NETWORK_TIMEOUT = 30
DEFAULT_PORT = 22
DEFAULT_POOL_SIZE = 6
DEFAULT_INSTANCE = 'Master'


HOSTNAME = 'host_name'
USERNAME = 'user_name'
PASSWORD = 'password'
PORT = 'port'
PRIVATE_KEY = 'private_key'
IS_SUDOER = 'is_sudoer'
INSTANCE = 'instance'

BASE_SCHEMA = {
    'items': [
        {'name': USERNAME, 'title': 'User Name', 'type': 'string'},
        {'name': PASSWORD, 'title': 'Password', 'type': 'string', 'format': 'password', 'default': ''},
        {
            'name': PRIVATE_KEY,
            'title': 'Private Key',
            'description': 'SSH Private key for authentication',
            'type': 'file',
        },
        {
            'name': PORT,
            'title': 'SSH Port',
            'type': 'integer',
            'default': DEFAULT_PORT,
            'description': 'Protocol Port',
        },
        {
            'name': IS_SUDOER,
            'title': 'Sudoer',
            'description': (
                'Use sudo to execute privileged commands. If left unchecked, privileged commands may fail.'
            ),
            'type': 'bool',
            'default': True,
        },
    ],
    'required': [USERNAME, IS_SUDOER],
    'type': 'array',
}

ACTION_SCHEMA = copy.deepcopy(BASE_SCHEMA)
INSTANCE_ITEM = {'name': INSTANCE, 'title': 'Instance Name', 'type': 'string', 'default': DEFAULT_INSTANCE}
ACTION_SCHEMA['items'].append(INSTANCE_ITEM)

ADAPTER_SCHEMA = copy.deepcopy(BASE_SCHEMA)
ADAPTER_SCHEMA['items'].insert(0, {'name': HOSTNAME, 'title': 'Host Name', 'type': 'string'})
ADAPTER_SCHEMA['required'].insert(0, HOSTNAME)
