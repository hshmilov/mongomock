DEFAULT_NETWORK_TIMEOUT = 30
DEFAULT_PORT = 22
DEFAULT_POOL_SIZE = 6


HOSTNAME = 'host_name'
USERNAME = 'user_name'
PASSWORD = 'password'
PORT = 'port'
PRIVATE_KEY = 'private_key'
IS_SUDOER = 'is_sudoer'

ACTION_SCHEMA = {
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
