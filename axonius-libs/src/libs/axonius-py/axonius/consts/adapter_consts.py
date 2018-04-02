from axonius.devices.dns_resolvable import DNSResolvableDevice

ADAPTER_PLUGIN_TYPE = 'Adapter'
SCANNER_ADAPTER_PLUGIN_SUBTYPE = 'Scanner'
DEVICE_ADAPTER_PLUGIN_SUBTYPE = 'Device'
IGNORE_DEVICE = "IgnoreDevice"
DEVICE_SAMPLE_RATE = 'device_sample_rate'

# Config
DEFAULT_SAMPLE_RATE = 'default_sample_rate'
DEFAULT_DEVICE_ALIVE_THRESHOLD_HOURS = 'default_device_alive_threshold_hours'
DEFAULT_USER_ALIVE_THRESHOLD_DAYS = 'default_user_alive_threshold_days'

# Active directory adapter
DNS_RESOLVE_STATUS = DNSResolvableDevice.dns_resolve_status.name
DEVICES_DATA = 'devices_data'
