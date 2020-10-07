# EC consts
API_ENDPOINT_BASE = 'api.dnsmadeeasy.com'
ADAPTER_NAME = 'dns_made_easy_adapter'
ACTION_CONFIG_PARENT_TAG = 'parent_tag'
# adapter consts
API_VERSION = 'V2.0'
ALL_DOMAINS_ENDPOINT = 'dns/managed'
STRFTIME_DATE_GMT = '%a, %d %b %Y %H:%M:%S GMT'
SOURCE_TYPE_BY_ID = {
    0: 'Template',
    1: 'Domain',
    2: 'Unknown'
}
# response header - used for rate limiting
REMAINING_REQUESTS_HEADER = 'x-dnsme-requestsRemaining'
# lower boundary for number of API calls remaining in REMAINING_REQUESTS_HEADER
#   if we are at or below this number, we will sleep for SLEEP_TIME
REQUEST_LIMIT = 8
# sleep for 3 minutes
SLEEP_TIME = 3 * 60
