import os
from axonius.utils.files import SHARED_READONLY_DIR

DEVICES_PER_PAGE = 1
MAX_DEVICES = 2000000
HTTP_RETRIES_ERROR = 409

INVENTORY_TYPE = 'inventory'
HOST_ASSET_TYPE = 'host_asset'
UNSCANNED_IP_TYPE = 'unscanned_ip'


QUALYS_SCANS_DOMAIN = 'Qualys_Scans_Domain'
USERNAME = 'username'
PASSWORD = 'password'
VERIFY_SSL = 'verify_ssl'
HTTPS_PROXY = 'https_proxy'
AGENT_DEVICE = 'agent_device'
SCAN_DEVICE = 'scan_device'
QUALYS_TAGS_WHITELIST = 'qualys_tags_white_list'

UNSCANNED_IP_URL_PREFIX = 'api/2.0/fo/asset/ip'
HOST_URL_PREFIX = 'api/2.0/fo/asset/host'
REPORT_URL_PREFIX = 'api/2.0/fo/report'
SCANS_URL_PREFIX = 'api/2.0/fo/'
ALL_HOSTS_URL = 'asset/host/'
ALL_HOSTS_PARAMS = f'action=list&details=All&truncation_limit={DEVICES_PER_PAGE}&id_min=0&show_tags=1'
ALL_HOSTS_OUTPUT = 'HOST_LIST_OUTPUT'

VM_HOST_URL = 'asset/host/vm/detection/'
VM_HOST_PARAMS = f'action=list&truncation_limit={DEVICES_PER_PAGE}&id_min=0&show_tags=1'
VM_HOST_OUTPUT = 'HOST_LIST_VM_DETECTION_OUTPUT'

QUALYS_FILE_DIR = os.path.join(SHARED_READONLY_DIR, 'qualys_vulnerabilities')
QUALYS_QID_TO_CVE_CSV = os.path.join(QUALYS_FILE_DIR, 'qualys_qid_to_cve.csv')
FETCH_EXCEPTION_THRESHOLD = 3

RETRY_SLEEP_TIME = 3
MAX_RETRIES = 3
DEFAULT_REQUEST_TIMEOUT = 200
DEFAULT_CHUNK_SIZE = 50

HOST_ASSET_FIELDS = []

JWT_TOKEN_REFRESH = 5400  # 1.5 Hours in seconds
INVENTORY_AUTH_API = 'auth'

ASSET_GROUP_MASTER_PREFIX = 'Master-'
