# IMPORTANT: Do not change these consts! There are alerts and notifications that parse logs using these strings


class SystemMetric:
    GUI_USERS = 'system.gui.users'
    DEVICES_SEEN = 'system.devices.seen'
    DEVICES_UNIQUE = 'system.devices.unique'
    USERS_SEEN = 'system.users.seen'
    USERS_UNIQUE = 'system.users.unique'
    ENFORCEMENT_RAW = 'enforcement_raw'
    ENFORCEMENTS_COUNT = 'enforcements_count'
    EC_ACTION_RAW = 'ec_action_raw'
    STORED_VIEW_RAW = 'stored_view_raw'
    STORED_VIEWS_COUNT = 'stored_views_count'
    TIMED_ENDPOINT = 'timed_endpoint'
    NETIFACES_COUNT = 'netifaces.count'
    HOST_DB_DISK_FREE = 'host.db_disk_free'
    HOST_DB_DISK_FREE_PERC = 'host.db_disk_free_percentage'
    HOST_ROOT_DISK_FREE = 'host.root_disk_free'
    HOST_ROOT_DISK_FREE_PERC = 'host.root_disk_free_percentage'
    HOST_VIRTUAL_MEMORY_TOTAL = 'host.virtual_memory.total'
    HOST_VIRTUAL_MEMORY_AVAILABLE = 'host.virtual_memory.available'
    HOST_VIRTUAL_MEMORY_PERCENT = 'host.virtual_memory.percent'
    HOST_SWAP_TOTAL = 'host.swap.total'
    HOST_SWAP_USED = 'host.swap.used'
    HOST_SWAP_FREE = 'host.swap.free'
    HOST_SWAP_PERCENT = 'host.swap.percent'
    HOST_DOCKER_STATS_KEY = 'host.docker_stats'
    CYCLE_FINISHED = 'cycle_finished'
    TRIAL_EXPIRED_STATE = 'trial_expired_state'
    CONTRACT_EXPIRED_STATE = 'contract_expired_state'
    LOGIN_MARKER = 'LOGIN_MARKER'
    NEW_NODE_CONNECTED = 'new_node_connected'


class ApiMetric:
    REQUEST_PATH = 'api.request.path'
    PUBLIC_REQUEST_PATH = 'public.request.path'


class Query:
    QUERY_GUI = 'query.gui'
    QUERY_HISTORY = 'query.history'


class Adapters:
    CREDENTIALS_CHANGE_OK = 'credentials_change.ok'
    CREDENTIALS_CHANGE_ERROR = 'credentials_change.error'
    CONNECTION_ESTABLISH_ERROR = 'adapter_connection_error'


class GettingStartedMetric:
    AUTO_OPEN_SETTING = 'getting_started.settings.auto_open'
    FEATURE_ENABLED_SETTING = 'getting_started.settings.feature_enabled'
    COMPLETION_STATE = 'getting_started.state.completion'


class InstancesMetrics:
    INSTANCE_LAST_SEEN = 'instance_last_seen'
