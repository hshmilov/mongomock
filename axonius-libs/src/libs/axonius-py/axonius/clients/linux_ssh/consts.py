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
        {'name': USERNAME, 'title': 'User Name', 'type': 'string'},
        {'name': PASSWORD, 'title': 'Password', 'type': 'string', 'format': 'password'},
        {
            'name': PRIVATE_KEY,
            'title': 'Private Key',
            'description': 'SSH Private Key for authentication',
            'type': 'file',
        },
        {
            'name': PASSPHRASE,
            'title': 'Private Key Passphrase',
            'description': 'SSH Private Key passphrase',
            'type': 'string',
            'format': 'password',
        },
        {
            'name': PORT,
            'title': 'SSH Port',
            'type': 'integer',
            'description': 'Protocol Port',
        },
        {
            'name': IS_SUDOER,
            'title': 'Sudoer',
            'description': (
                'Use sudo to execute privileged commands. If left unchecked, privileged commands may fail.'
            ),
            'type': 'bool',
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
CMDNAME_ITEM = {'name': COMMAND_NAME, 'title': 'Command Name', 'type': 'string'}
UPLOAD_PATH_ITEM = {'name': UPLOAD_PATH_NAME, 'title': 'Upload Path', 'type': 'string'}
SHOULD_DELETE_AFTER_EXEC = {'name': SHOULD_DELETE_AFTER_EXEC_NAME,
                            'title': 'Delete Files After Execution', 'type': 'bool'}
UPLOAD_PERMISSIONS = {'name': UPLOAD_PERMISSIONS_NAME, 'title': 'Upload Files Permissions', 'type': 'integer',
                      'default': DEFAULT_UPLOAD_PERMISSIONS}
EXTRA_FILES = {
    'name': EXTRA_FILES_NAME,
    'title': 'Files to deploy',
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

ADAPTER_SCHEMA['items'].insert(0, {'name': HOSTNAME, 'title': 'Host Name', 'type': 'string'})
ADAPTER_SCHEMA['required'].insert(0, HOSTNAME)
