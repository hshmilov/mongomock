from pathlib import Path

# PATHS #
VOLATILE_CONFIG_PATH = '/home/axonius/plugin_volatile_config.ini'
SHARED_READONLY_DIR_NAME = 'shared_readonly_files'
SHARED_READONLY_FULL_PATH = Path('/home/axonius') / SHARED_READONLY_DIR_NAME
AXONIUS_SETTINGS_DIR_NAME = '.axonius_settings'
METADATA_PATH = SHARED_READONLY_FULL_PATH / '__build_metadata'
ENCRYPTION_KEY_FILENAME = '.__key'
ENCRYPTION_KEY_PATH = SHARED_READONLY_FULL_PATH / ENCRYPTION_KEY_FILENAME

# SERVICES #
CORE_UNIQUE_NAME = 'core'
AGGREGATOR_PLUGIN_NAME = 'aggregator'
GUI_NAME = 'gui'
STATIC_CORRELATOR_PLUGIN_NAME = 'static_correlator'
SYSTEM_SCHEDULER_PLUGIN_NAME = 'system_scheduler'
DEVICE_CONTROL_PLUGIN_NAME = 'device_control'

# FIELDS #
ADAPTERS_LIST_LENGTH = 'adapter_list_length'
PLUGIN_UNIQUE_NAME = 'plugin_unique_name'
PLUGIN_NAME = 'plugin_name'
NODE_ID = 'node_id'
NODE_USER_PASSWORD = 'node_user_password'
NODE_INIT_NAME = 'node_init_name'
NODE_NAME = 'node_name'
NOTES_DATA_TAG = 'Notes'

# SETTINGS #
SYSTEM_SETTINGS = 'system_settings'
PROXY_SETTINGS = 'proxy_settings'
PROXY_ADDR = 'proxy_addr'
PROXY_PORT = 'proxy_port'
PROXY_USER = 'proxy_user'
PROXY_PASSW = 'proxy_password'
NOTIFICATIONS_SETTINGS = 'notifications_settings'
NOTIFY_ADAPTERS_FETCH = 'notify_adapters_fetch'
CORRELATION_SETTINGS = 'correlation_settings'
CORRELATE_BY_EMAIL_PREFIX = 'correlate_by_email_prefix'

# COLLECTIONS #
CONFIGURABLE_CONFIGS_COLLECTION = 'configurable_configs'
DASHBOARD_COLLECTION = 'dashboard'
VERSION_COLLECTION = 'version'
GUI_SYSTEM_CONFIG_COLLECTION = 'system_config'
MAINTENANCE_TYPE = 'maintenance'

AXONIUS_USER_NAME = '_axonius'

X_UI_USER = 'x-ui-user'
X_UI_USER_SOURCE = 'x-ui-user-source'

AXONIUS_NETWORK = 'axonius'
WEAVE_NETWORK = 'axonius-weave'
WEAVE_PATH = '/usr/local/bin/weave'
