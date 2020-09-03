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

NON_THREAD_SAFE_CLEAN_DB_ADAPTERS = ['aws_adapter']

# Enterprise Password Mgr
VAULT_PROVIDER = 'vault_provider'
LEGACY_VAULT_PROVIDER = 'cyberark_vault'

# CSV Location
AVAILABLE_CSV_LOCATION_FIELDS = ['subnet', 'location', 'location_name', 'location_id', 'region', 'zone', 'country',
                                 'street_address', 'facility_name', 'facility_id', 'city', 'state', 'postal_code',
                                 'full_address', 'latitude', 'longitude', 'ad_sitename', 'ad_sitecode', 'comments',
                                 'site_criticality', 'site_function', 'gsc_sitecode', 'talentlink_sitecode',
                                 'security_level']
