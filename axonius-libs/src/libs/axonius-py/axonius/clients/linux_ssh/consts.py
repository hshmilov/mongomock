import copy
from collections import namedtuple

DEFAULT_NETWORK_TIMEOUT = 30
DEFAULT_PORT = 22
DEFAULT_POOL_SIZE = 6

HOSTNAME = 'host_name'
USERNAME = 'user_name'
PASSWORD = 'password'
PORT = 'port'
PRIVATE_KEY = 'private_key'
IS_SUDOER = 'is_sudoer'
PASSPHRASE = 'passphrase'
SUDO_PATH = 'sudo_path'
COMMAND = 'command'
COMMAND_NAME = 'command_name'
ACTION_TYPES = namedtuple('ActionTypes', ('scan', 'cmd'))(scan='execute_scan', cmd='execute_cmd')

EXTRA_FILES_NAME = 'extra_files'
DEFAULT_UPLOAD_PATH = '/tmp'
DEFAULT_UPLOAD_PERMISSIONS = 777
UPLOAD_PATH_NAME = 'upload_path'
SHOULD_DELETE_AFTER_EXEC_NAME = 'should_delete_after_exec'
UPLOAD_PERMISSIONS_NAME = 'upload_permissions'
BASE_SCHEMA = {
    'items': [
        {'name': USERNAME, 'title': 'User name', 'type': 'string'},
        {'name': PASSWORD, 'title': 'Password', 'type': 'string', 'format': 'password'},
        {
            'name': PRIVATE_KEY,
            'title': 'Private key',
            'description': 'SSH private key for authentication',
            'type': 'file',
        },
        {
            'name': PASSPHRASE,
            'title': 'Private key passphrase',
            'description': 'SSH private key passphrase',
            'type': 'string',
            'format': 'password',
        },
        {
            'name': PORT,
            'title': 'SSH port',
            'type': 'integer',
            'description': 'Protocol port',
        },
        {
            'name': IS_SUDOER,
            'title': 'Sudoer',
            'description': (
                'Use sudo to execute privileged commands. If left unchecked, privileged commands may fail.'
            ),
            'type': 'bool',
        },
        {
            'name': SUDO_PATH,
            'title': 'Sudo path',
            'type': 'string'
        },
    ],
    'required': [USERNAME, IS_SUDOER],
    'type': 'array',
}

BASE_DEFAULTS_SCHEMA = {PORT: DEFAULT_PORT,
                        IS_SUDOER: True,
                        PASSWORD: ''}

SCAN_ACTION_SCHEMA = copy.deepcopy(BASE_SCHEMA)

CMD_ACTION_SCHEMA = copy.deepcopy(BASE_SCHEMA)
CMD_ITEM = {'name': COMMAND, 'title': 'Command', 'type': 'string'}
CMDNAME_ITEM = {'name': COMMAND_NAME, 'title': 'Command name', 'type': 'string'}
UPLOAD_PATH_ITEM = {'name': UPLOAD_PATH_NAME, 'title': 'Upload path', 'type': 'string'}
SHOULD_DELETE_AFTER_EXEC = {'name': SHOULD_DELETE_AFTER_EXEC_NAME,
                            'title': 'Delete files after execution', 'type': 'bool'}
UPLOAD_PERMISSIONS = {'name': UPLOAD_PERMISSIONS_NAME, 'title': 'Upload files permissions', 'type': 'integer',
                      'default': DEFAULT_UPLOAD_PERMISSIONS}
EXTRA_FILES = {
    'name': EXTRA_FILES_NAME,
    'title': 'Files to Deploy',
    'type': 'array',
    'items':
        {
            'name': 'file',
            'title': 'File',
            'type': 'file',
            'items': [
                {
                    'name': 'file',
                    'title': 'File',
                    'type': 'file'
                }
            ]
        }
}

CMD_ACTION_SCHEMA['items'].append(CMD_ITEM)
CMD_ACTION_SCHEMA['items'].append(CMDNAME_ITEM)
CMD_ACTION_SCHEMA['items'].append(EXTRA_FILES)
CMD_ACTION_SCHEMA['items'].append(UPLOAD_PATH_ITEM)
CMD_ACTION_SCHEMA['items'].append(SHOULD_DELETE_AFTER_EXEC)
CMD_ACTION_SCHEMA['items'].append(UPLOAD_PERMISSIONS)
CMD_ACTION_SCHEMA['required'].append(COMMAND)
CMD_ACTION_SCHEMA['required'].append(COMMAND_NAME)

ADAPTER_SCHEMA = copy.deepcopy(BASE_SCHEMA)

# Setting up defaults for adapter_schema
for current_item in ADAPTER_SCHEMA['items']:
    if current_item['name'] in BASE_DEFAULTS_SCHEMA:
        current_item['default'] = BASE_DEFAULTS_SCHEMA[current_item['name']]

ADAPTER_SCHEMA['items'].insert(0, {'name': HOSTNAME, 'title': 'Host name', 'type': 'string'})
ADAPTER_SCHEMA['required'].insert(0, HOSTNAME)
