from pathlib import Path

# PATHS #

VOLATILE_CONFIG_PATH = '/home/axonius/plugin_volatile_config.ini'
SHARED_READONLY_DIR_NAME = 'shared_readonly_files'
SHARED_READONLY_FULL_PATH = Path('/home/axonius') / SHARED_READONLY_DIR_NAME
AXONIUS_SETTINGS_DIR_NAME = '.axonius_settings'
AXONIUS_SETTINGS_PATH = Path('/home/axonius/') / AXONIUS_SETTINGS_DIR_NAME
NODE_ID_FILENAME = '.node_id'
NODE_ID_PATH = AXONIUS_SETTINGS_PATH / NODE_ID_FILENAME
METADATA_PATH = SHARED_READONLY_FULL_PATH / '__build_metadata'
LIBS_PATH = Path('/home/axonius/libs')
DB_KEY_FILENAME = '.db_key'
DB_KEY_PATH = AXONIUS_SETTINGS_PATH / DB_KEY_FILENAME

# SERVICES #
CORE_UNIQUE_NAME = 'core'
AGGREGATOR_PLUGIN_NAME = 'aggregator'
GUI_PLUGIN_NAME = 'gui'
STATIC_CORRELATOR_PLUGIN_NAME = 'static_correlator'
STATIC_USERS_CORRELATOR_PLUGIN_NAME = 'static_users_correlator'
SYSTEM_SCHEDULER_PLUGIN_NAME = 'system_scheduler'
REPORTS_PLUGIN_NAME = 'reports'
COMPLIANCE_PLUGIN_NAME = 'compliance'
EXECUTION_PLUGIN_NAME = 'execution'
DEVICE_CONTROL_PLUGIN_NAME = 'device_control'
GENERAL_INFO_PLUGIN_NAME = 'general_info'
AXONIUS_DNS_SUFFIX = 'axonius.local'
HEAVY_LIFTING_PLUGIN_NAME = 'heavy_lifting_plugin'
STATIC_ANALYSIS_PLUGIN_NAME = 'static_analysis'
REIMAGE_TAGS_ANALYSIS_PLUGIN_NAME = 'reimage_tags_analysis'
MASTER_PROXY_PLUGIN_NAME = 'master-proxy'

# ADAPTERS #
ACTIVE_DIRECTORY_PLUGIN_NAME = 'active_directory_adapter'
LINUX_SSH_PLUGIN_NAME = 'linux_ssh_adapter'
SHODAN_PLUGIN_NAME = 'shodan_adapter'
PORTNOX_PLUGIN_NAME = 'portnox'
CENSYS_PLUGIN_NAME = 'censys_adapter'
HAVEIBEENPWNED_PLUGIN_NAME = 'haveibeenpwned_adapter'
WEBSCAN_PLUGIN_NAME = 'webscan_adapter'

# FIELDS #
ADAPTERS_LIST_LENGTH = 'adapter_list_length'
PLUGIN_UNIQUE_NAME = 'plugin_unique_name'
PLUGIN_NAME = 'plugin_name'
FIRST_FETCH_TIME = 'first_fetch_time'
FETCH_TIME = 'fetch_time'
NODE_ID = 'node_id'
NODE_DATA_INSTANCE_ID = 'nodeIds'
NODE_USER_PASSWORD = 'node_user_password'
NODE_INIT_NAME = 'node_init_name'
NODE_NAME = 'node_name'
NOTES_DATA_TAG = 'Notes'
NODE_STATUS = 'status'
NODE_HOSTNAME = 'hostname'
NODE_USE_AS_ENV_NAME = 'use_as_environment_name'
NODE_IP_LIST = 'ips'
NODE_ID_ENV_VAR_NAME = 'NODE_ID'
DB_KEY_ENV_VAR_NAME = 'DB_KEY'

# SETTINGS #
SYSTEM_SETTINGS = 'system_settings'
PROXY_SETTINGS = 'proxy_settings'
PROXY_ADDR = 'proxy_addr'
PROXY_PORT = 'proxy_port'
PROXY_USER = 'proxy_user'
PROXY_PASSW = 'proxy_password'
PROXY_VERIFY = 'proxy_verify'
PROXY_FOR_ADAPTERS = 'proxy_for_adapters'

NOTIFICATIONS_SETTINGS = 'notifications_settings'
NOTIFICATIONS_COLLECTION = 'notifications'
NOTIFY_ADAPTERS_FETCH = 'notify_adapters_fetch'
ADAPTERS_ERRORS_MAIL_ADDRESS = 'adapter_errors_mail_address'
ADAPTERS_ERRORS_WEBHOOK_ADDRESS = 'adapters_webhook_address'
STATIC_ANALYSIS_SETTINGS = 'static_analysis_settings'
CORRELATION_SETTINGS = 'correlation_settings'
CORRELATE_AD_DISPLAY_NAME = 'correlate_by_ad_display_name'
CORRELATE_BY_EMAIL_PREFIX = 'correlate_by_email_prefix'
CORRELATE_BY_USERNAME_DOMAIN_ONLY = 'correlate_by_username_domain_only'
CORRELATE_AD_SCCM = 'correlate_ad_sccm'
CSV_FULL_HOSTNAME = 'csv_full_hostname'
CORRELATE_BY_SNOW_MAC = 'correlate_by_snow_mac'
CORRELATE_BY_AZURE_AD_NAME_ONLY = 'correlate_azure_ad_name_only'
CORRELATION_SCHEDULE = 'correlation_schedule'
CORRELATION_SCHEDULE_ENABLED = 'enabled'
CORRELATION_SCHEDULE_HOURS_INTERVAL = 'correlation_hours_interval'
FETCH_EMPTY_VENDOR_SOFTWARE_VULNERABILITES = 'fetch_empty_vendor_software_vulnerabilites'
AGGREGATION_SETTINGS = 'aggregation_settings'
MAX_WORKERS = 'max_workers'
SOCKET_READ_TIMEOUT = 'socket_read_timeout'
UPPERCASE_HOSTNAMES = 'uppercase_hostnames'

# PASSWORD SETTINGS #
PASSWORD_SETTINGS = 'password_policy_settings'
PASSWORD_LENGTH_SETTING = 'password_length'
PASSWORD_MIN_LOWERCASE = 'password_min_lowercase'
PASSWORD_MIN_UPPERCASE = 'password_min_uppercase'
PASSWORD_MIN_NUMBERS = 'password_min_numbers'
PASSWORD_MIN_SPECIAL_CHARS = 'password_min_special_chars'
PASSWORD_NO_MEET_REQUIREMENTS_MSG = 'Password does not meet the password policy requirements'
PASSWORD_BRUTE_FORCE_PROTECTION = 'password_brute_force_protection'
PASSWORD_PROTECTION_ALLOWED_RETRIES = 'password_max_allowed_tries'
PASSWORD_PROTECTION_LOCKOUT_MIN = 'password_lockout_minutes'
PASSWORD_PROTECTION_BY_IP = 'password_protection_by_ip'
PASSWORD_PROTECTION_BY_USERNAME = 'password_protection_by_username'

# COLLECTIONS #
CONFIGURABLE_CONFIGS_COLLECTION = 'configurable_configs'
REPORTS_CONFIG_COLLECTION = 'reports_config'
VERSION_COLLECTION = 'version'
GUI_SYSTEM_CONFIG_COLLECTION = 'system_config'
MAINTENANCE_TYPE = 'maintenance'
GLOBAL_KEYVAL_COLLECTION = 'global_keyval'
KEYS_COLLECTION = 'keys.client_config'
DEVICE_VIEWS = 'device_views'
USER_VIEWS = 'user_views'

ADMIN_USER_NAME = 'admin'
AXONIUS_USER_NAME = '_axonius'
AXONIUS_RO_USER_NAME = '_axonius_ro'
AXONIUS_USERS_LIST = [AXONIUS_USER_NAME, AXONIUS_RO_USER_NAME]
PREDEFINED_USER_NAMES = [ADMIN_USER_NAME, AXONIUS_USER_NAME, AXONIUS_RO_USER_NAME]

X_UI_USER = 'x-ui-user'
X_UI_USER_SOURCE = 'x-ui-user-source'

# Defaults
DEFAULT_SOCKET_READ_TIMEOUT = 5
DEFAULT_SOCKET_RECV_TIMEOUT = 300
