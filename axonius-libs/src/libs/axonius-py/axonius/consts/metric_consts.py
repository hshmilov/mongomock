# IMPORTANT: Do not change these consts! There are alerts and notifications that parse logs using these strings


class SystemMetric:
    GUI_USERS = 'system.gui.users'
    DEVICES_SEEN = 'system.devices.seen'
    DEVICES_UNIQUE = 'system.devices.unique'
    USERS_SEEN = 'system.users.seen'
    USERS_UNIQUE = 'system.users.unique'
    ENFORCEMENT_RAW = 'system.alert.raw'
    TIMED_ENDPOINT = 'timed_endpoint'
    NETIFACES_COUNT = 'netifaces.count'
    HOST_DB_DISK_FREE_BYTES = 'host.db_disk_free_bytes'
    HOST_DB_DISK_FREE_PERC = 'host.db_disk_free_percentage'
    HOST_ROOT_DISK_FREE_BYTES = 'host.root_disk_free_bytes'
    HOST_ROOT_DISK_FREE_PERC = 'host.root_disk_free_percentage'


class ApiMetric:
    REQUEST_PATH = 'api.request.path'
    PUBLIC_REQUEST_PATH = 'public.request.path'


class Query:
    QUERY_GUI = 'query.gui'
    QUERY_HISTORY = 'query.history'


class Adapters:
    CREDENTIALS_CHANGE_OK = 'credentials_change.ok'
    CREDENTIALS_CHANGE_ERROR = 'credentials_change.error'
