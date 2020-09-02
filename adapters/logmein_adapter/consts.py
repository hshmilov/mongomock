import re

MAX_NUMBER_OF_DEVICES = 2000000
MAX_NUMBER_OF_USERS = 20000000
URL_AUTH_SUFFIX = r'public-api/v1/authentication'
URL_DEVICES_SUFFIX = r'public-api/v2/hostswithgroups'
URL_USERS_SUFFIX = r'public-api/v2/users'
URL_HARDWARE_FIELDS = r'public-api/v1/inventory/hardware/fields'
URL_SYSTEM_FIELDS = r'public-api/v1/inventory/system/fields'
URL_HARDWARE_REPORT = r'public-api/v1/inventory/hardware/reports'
URL_SYSTEM_REPORT = r'public-api/v1/inventory/system/reports'
URL_ANTI_VIRUS = r'public-api/v1/hosts/anti-virus/details'
URL_COMPUTER_REPORT = r'public-api/v1/reports/computer-status'
EXTRA_DETAILS_NAME = 'extra_{name}_details'
REPORT_MAX_SIZE = 50
PAREN_RE = re.compile(r'\([^)]+?\)')
