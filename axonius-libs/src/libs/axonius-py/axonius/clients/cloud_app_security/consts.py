LOGS_PER_PAGE = 200
MAX_NUMBER_OF_USERS = 10000000
MAX_LOGS_PER_USER = 1000

SCRAPE_DATE_HOURS_AGO = 3
MAX_SCRAPE_DATE_HOURS_AGO = 72
DEFAULT_ASYNC_CHUNKS_SIZE = 50

URL_BASE_PREFIX = 'v1'
API_URL_SECURITY_LOG_SUFFIX = 'siem/security_events'

ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# Only email services for now
API_SERVICE_PARAMETERS = ['exchange', 'gmail', 'exchangeserver']
API_EVENT_PARAMETERS = ['securityrisk', 'virtualanalyzer', 'ransomware', 'dlp']
