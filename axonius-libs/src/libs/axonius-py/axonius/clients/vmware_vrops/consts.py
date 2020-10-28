DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 20000000
DEFAULT_TIMEOUT_HOURS = 6

TOKEN_URL = 'auth/token/acquire'
RESOURCES_URL = 'resources'
ALERTS_URL = 'alerts'
VIRTUAL_MACHINE_PROPERTIES_URL = 'adapterkinds/VMWARE/resourcekinds/VirtualMachine/properties'
HOST_SYSTEM_PROPERTIES_URL = 'adapterkinds/VMWARE/resourcekinds/HostSystem/properties'
PROPERTIES_URL = 'resources/properties/latest/query'
SECOND_PROPERTIES_URL = 'resources/properties'

PROPERTIES_BLACK_LIST = ['summary|UUID', 'System Properties|resource_kind_type',
                         'System Properties|resource_kind_subtype', 'summary|MOID']
