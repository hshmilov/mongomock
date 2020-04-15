import re
from datetime import timedelta

DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000

DEFAULT_DOMAIN = 'https://service.sumologic.com'

DOMAIN_RE = re.compile(r'https://service\.(?P<sumologic_deployment>(?:[^.]+?\.)?sumologic.com/?)')
DOMAIN_API_URL_PREFIX = r'https://api.'
DOMAIN_TO_API_RE_REPLACE = fr'{DOMAIN_API_URL_PREFIX}\g<sumologic_deployment>'

ENDPOINT_SEARCH_JOBS = 'search/jobs'

STATUS_SEARCH_JOB_COMPLETED = 'DONE GATHERING RESULTS'
STATUS_SEARCH_JOB_CANCELLED = 'CANCELLED'
SEARCH_JOB_EXIT_STATES = [STATUS_SEARCH_JOB_COMPLETED, STATUS_SEARCH_JOB_CANCELLED]
SEARCH_JOB_STATES = ['NOT STARTED', 'GATHERING RESULTS', 'FORCE PAUSED'] + SEARCH_JOB_EXIT_STATES
SEARCH_QUERY_DT_FORMATS = '%Y-%m-%dT%H:%M:%S'

PAGINATION_OFFSET_FIELD = 'offset'
PAGINATION_PER_PAGE_FIELD = 'limit'

DEVICES_IDENTIFIER_FIELDS = ['id', 'serial', 'mac_address', 'hostname', 'name']

MAX_WAIT_SEARCH_JOB = timedelta(hours=10)
EXECUTION_NOTICE_PERIOD = timedelta(minutes=10)
