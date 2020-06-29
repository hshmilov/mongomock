from axonius.devices.dns_resolvable import DNSResolvableDevice

ADAPTER_PLUGIN_TYPE = 'Adapter'
IGNORE_DEVICE = 'IgnoreDevice'

# Active directory adapter
DNS_RESOLVE_STATUS = DNSResolvableDevice.dns_resolve_status.name
IPS_FIELDNAME = 'ips'
NETWORK_INTERFACES_FIELDNAME = 'network_interfaces'
DEVICES_DATA = 'devices_data'

# Adapter Settings
SHOULD_NOT_REFRESH_CLIENTS = 'should_not_refresh_clients'
LAST_FETCH_TIME = 'last_fetch_time'

# Adapter Client Connection Label
CONNECTION_LABEL = 'connection_label'
# Adapter Client Config
CLIENT_CONFIG = 'client_config'
CLIENT_PASSWORD = 'password'

MAX_ASYNC_FETCH_WORKERS = 10

# adapter client id attribute
CLIENT_ID = 'client_id'

DEFAULT_PARALLEL_COUNT = 5

# Enterprise Password Mgr
VAULT_PROVIDER = 'vault_provider'
LEGACY_VAULT_PROVIDER = 'cyberark_vault'
