PAGE_SIZE_GET = 1000
PAGE_SIZE_GET_RESULT = 1000
PAGE_SIZE_DISCOVER = 100

RETRIES_REFRESH = 15

CACHE_EXPIRATION = 900
MAX_DEVICES_COUNT = 10000000

KNOWN_SENSORS = [
    'Computer ID',
    'Computer Name',
    'Computer Serial Number',
    'IP Address',
    'Installed Applications',
    'Tanium Client Version',
    'Last Reboot',
    'CPU Details',
    'Custom Tags',
    'Chassis Type',
    'Disk Drives',
    'Last Logged In User',
    'Manufacturer',
    'Model',
    'Operating System',
    'RAM',
    'Running Applications',
    'Running Service',
    'Service Details',
    'Service Pack',
    'x64/x86?',
    'Virtual Platform',
    'User Sessions',
    'USB Device Details',
    'Tanium Server Name List',
    'Tanium Server Version',
    'Time Zone',
]

REFRESH = True
MAX_HOURS = 0
# SQ_NAME = 'Multiplex'
SQ_NAME = 'Network Adapter Information'
# SQ_NAME = 'is online'
GET_DISCOVER_ASSETS = True
ENDPOINT_TYPE = 'Endpoint Type'
DISCOVERY_TYPE = 'Discovery Device'
DISCOVER_METHODS = ['arp', 'connected', 'script', 'nmap', 'managed']
