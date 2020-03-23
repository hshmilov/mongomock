PAGE_SLEEP = 1
PAGE_ATTEMPTS = 10
PAGE_SIZE = 100
MAX_DEVICES_COUNT = 20000000
METHODS = ['arp', 'connected', 'script', 'nmap', 'managed']
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'axonius/tanium_discover_adapter',
}
SELECT_FIELDS = [
    'cloudTags',
    'computerid',
    'createdAt',
    'hostname',
    'ignored',
    'imageId',
    'instanceId',
    'instanceState',
    'instanceType',
    'ipaddress',
    'ismanaged',
    'lastDiscoveredAt',
    'lastManagedAt',
    'launchTime',
    'locations',
    'macaddress',
    'macorganization',
    'method',
    'natipaddress',
    'networkId',
    'os',
    'osgeneration',
    'ownerId',
    'ports',
    'profile',
    'provider',
    'tags',
    'unmanageable',
    'updatedAt',
    'zone',
]
REPORT_KEYS = ['Name', 'Filter', 'Id']

REPORTS_OLD = {
    'v1': [
        {
            'Id': 'unmanaged',
            'Value': 'Unmanaged',
            'Name': 'All Unmanaged Interfaces',
            'Filter': [
                {'isDefault': True, 'field': 'computerid', 'operator': 'eq', 'value': '0'},
                {'isDefault': True, 'field': 'unmanageable', 'operator': 'neq', 'value': '1'},
                {'isDefault': True, 'field': 'unmanageable', 'operator': 'neq', 'value': '3'},
            ],
        },
        {
            'Id': 'managed',
            'Name': 'All Managed Interfaces',
            'Filter': [{'isDefault': True, 'field': 'computerid', 'operator': 'neq', 'value': '0'}],
        },
        {
            'Id': 'unmanageable',
            'Name': 'All Unmanageable Interfaces',
            'Filter': [
                {'isDefault': True, 'field': 'unmanageable', 'operator': 'neq', 'value': '0'},
                {'isDefault': True, 'field': 'unmanageable', 'operator': 'neq', 'value': '2'},
            ],
        },
        {'Filter': [], 'Id': 'ignored', 'IncludeIgnored': True, 'Name': 'Ignored Interfaces'},
    ]
}
SELECT_FAIL = r'no such column: .*\.(\w+)'
FETCH_OPTS = [
    {'name': 'fetch_unmanaged', 'report_id': 'unmanaged', 'title': 'Fetch Unmanaged', 'type': 'bool', 'default': True},
    {
        'name': 'fetch_unmanageable',
        'report_id': 'unmanageable',
        'title': 'Fetch Unmanageable',
        'type': 'bool',
        'default': True,
    },
    {'name': 'fetch_managed', 'report_id': 'managed', 'title': 'Fetch Managed', 'type': 'bool', 'default': False},
    {'name': 'fetch_ignored', 'report_id': 'ignored', 'title': 'Fetch Ignored', 'type': 'bool', 'default': True},
]
