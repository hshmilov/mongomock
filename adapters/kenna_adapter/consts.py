import re

DEVICE_PER_PAGE = 1000
MAX_NUMBER_OF_DEVICES = 2000000

DEFAULT_DOMAIN = 'https://api.kennasecurity.com'
DOMAIN_RE = re.compile(r'https://(?P<company_name>[^.]+)\.(?P<rest_url>(?:[^.]+\.)*?kennasecurity\.com)/?')
DOMAIN_TO_API_RE_REPLACE = r'https://api.\g<rest_url>'
