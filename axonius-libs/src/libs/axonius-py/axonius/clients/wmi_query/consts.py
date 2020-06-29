import copy
from collections import namedtuple

USERNAME = 'username'
PASSWORD = 'password'
DNS_SERVERS = 'dns_servers'
HOSTNAMES = 'hostnames'
PARAMS_NAME = 'params'
EXTRA_FILES_NAME = 'extra_files'
COMMAND_NAME = 'command_name'
REGISTRY_EXISTS = 'reg_check_exists'
USE_AD_CREDS = 'use_adapter'

ACTION_TYPES = namedtuple('ActionTypes', ('scan', 'cmd'))(scan='execute_scan', cmd='execute_cmd')
SCAN_CHUNK_SIZE = 1000
EXEC_CHUNK_SIZE = 1000
WMI_SCAN_PORTS = [135, 445]
BASE_SCHEMA = {
    'items': [
        {
            'name': USERNAME,
            'title': 'User name',
            'type': 'string'
        },
        {
            'name': PASSWORD,
            'title': 'Password',
            'type': 'string',
            'format': 'password'
        },
        {
            'name': DNS_SERVERS,
            'title': 'DNS servers',
            'type': 'string'
        },
    ],
    'type': 'array'
}
FILES_SCHEMA = {
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

USE_ADAPTER_SCHEMA = {
    'name': USE_AD_CREDS,
    'title': 'Use stored credentials from the Active Directory adapter',
    'type': 'bool',
}

# schema for wmi adapter
ADAPTER_SCHEMA = copy.deepcopy(BASE_SCHEMA)
ADAPTER_SCHEMA['items'].insert(0, {
    'name': HOSTNAMES,
    'title': 'Hostnames / IPs / CIDRs List',
    'type': 'string'
})
ADAPTER_SCHEMA['required'] = [HOSTNAMES, USERNAME, PASSWORD]

# Schema for wmi execute action
CMD_ACTION_SCHEMA = copy.deepcopy(BASE_SCHEMA)
CMD_ACTION_SCHEMA['items'].append({
    'name': PARAMS_NAME,
    'title': 'Command',
    'type': 'string'
})
CMD_ACTION_SCHEMA['items'].append({
    'name': COMMAND_NAME,
    'title': 'Command name',
    'type': 'string'
})
CMD_ACTION_SCHEMA['items'].append(FILES_SCHEMA)
CMD_ACTION_SCHEMA['items'].insert(0, USE_ADAPTER_SCHEMA)
CMD_ACTION_SCHEMA['required'] = [USE_AD_CREDS]

# Schema for wmi scan action
SCAN_ACTION_SCHEMA = copy.deepcopy(BASE_SCHEMA)
SCAN_ACTION_SCHEMA['items'].append({
    'name': REGISTRY_EXISTS,
    'title': 'Registry keys to check for existence',
    'type': 'array',
    'items': {
        'type': 'string'
    }
})
SCAN_ACTION_SCHEMA['items'].insert(0, USE_ADAPTER_SCHEMA)
SCAN_ACTION_SCHEMA['required'] = [USE_AD_CREDS]
