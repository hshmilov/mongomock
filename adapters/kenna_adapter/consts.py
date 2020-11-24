import re

DEVICE_PER_PAGE = 1000
MAX_NUMBER_OF_DEVICES = 2000000

DEFAULT_DOMAIN = 'https://api.kennasecurity.com'
DOMAIN_RE = re.compile(r'https://(?P<company_name>[^.]+)\.(?P<rest_url>(?:[^.]+\.)*?kennasecurity\.com)/?')
DOMAIN_TO_API_RE_REPLACE = r'https://api.\g<rest_url>'

# 12 hours
MAX_EXPORT_EXECUTION_TIME = 12 * 60 * 60
EXPORT_SAMPLE_SLEEP_TIME = 60

# The export is currently processing. Try again later.
EXPORT_STATUS_RETRY = 'The export is currently processing'
EXPIRT_SINCE_DT_FORMAT = '%Y-%m-%d %H:%M:%S'

# 422 Unprocessable Entity - {
#     "search_id": 1,
#     "record_count": 94,
#     "error_message": "A duplicate export exists that has not processed."
# }
EXPORT_ERROR_EXISTING = 422
EXPORT_VALID_ERROR_CODES = [200, EXPORT_ERROR_EXISTING]
