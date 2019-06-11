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

# SERVICES #
CORE_UNIQUE_NAME = 'core'
AGGREGATOR_PLUGIN_NAME = 'aggregator'
GUI_PLUGIN_NAME = 'gui'
STATIC_CORRELATOR_PLUGIN_NAME = 'static_correlator'
STATIC_USERS_CORRELATOR_PLUGIN_NAME = 'static_users_correlator'
SYSTEM_SCHEDULER_PLUGIN_NAME = 'system_scheduler'
DEVICE_CONTROL_PLUGIN_NAME = 'device_control'
GENERAL_INFO_PLUGIN_NAME = 'general_info'
HEAVY_LIFTING_PLUGIN_NAME = 'heavy_lifting_plugin'
STATIC_ANALYSIS_PLUGIN_NAME = 'static_analysis'
REPORTS_PLUGIN_NAME = 'reports'
REIMAGE_TAGS_ANALYSIS_PLUGIN_NAME = 'reimage_tags_analysis'
EXECUTION_PLUGIN_NAME = 'execution'

# ADAPTERS #
ACTIVE_DIRECTORY_PLUGIN_NAME = 'active_directory_adapter'
LINUX_SSH_PLUGIN_NAME = 'linux_ssh_adapter'
SHODAN_PLUGIN_NAME = 'shodan_adapter'

# FIELDS #
ADAPTERS_LIST_LENGTH = 'adapter_list_length'
PLUGIN_UNIQUE_NAME = 'plugin_unique_name'
PLUGIN_NAME = 'plugin_name'
NODE_ID = 'node_id'
NODE_USER_PASSWORD = 'node_user_password'
NODE_INIT_NAME = 'node_init_name'
NODE_NAME = 'node_name'
NOTES_DATA_TAG = 'Notes'
NODE_ID_ENV_VAR_NAME = 'NODE_ID'

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
NOTIFY_ADAPTERS_FETCH = 'notify_adapters_fetch'
ADAPTERS_ERRORS_MAIL_ADDRESS = 'adapter_errors_mail_address'
CORRELATION_SETTINGS = 'correlation_settings'
CORRELATE_BY_EMAIL_PREFIX = 'correlate_by_email_prefix'
AGGREGATION_SETTINGS = 'aggregation_settings'
MAX_WORKERS = 'max_workers'

# COLLECTIONS #
CONFIGURABLE_CONFIGS_COLLECTION = 'configurable_configs'
VERSION_COLLECTION = 'version'
GUI_SYSTEM_CONFIG_COLLECTION = 'system_config'
MAINTENANCE_TYPE = 'maintenance'
GLOBAL_KEYVAL_COLLECTION = 'global_keyval'

AXONIUS_USER_NAME = '_axonius'

X_UI_USER = 'x-ui-user'
X_UI_USER_SOURCE = 'x-ui-user-source'
