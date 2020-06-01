import re

from axonius.devices.device_adapter import DeviceRunningState

AZURE_CHINA_LOGIN_URL = 'https://login.chinacloudapi.cn'
AZURE_CHINA_MGMT_URL = 'https://management.chinacloudapi.cn'
AZURE_USGOV_LOGIN_URL = 'https://login.microsoftonline.us'
AZURE_USGOV_MGMT_URL = 'https://management.usgovcloudapi.net'
AZURE_DEGOV_LOGIN_URL = 'https://login.microsoftonline.de'
AZURE_DEGOV_MGMT_URL = 'https://management.microsoftazure.de'
AZURE_DEFAULT_LOGIN_URL = 'https://login.microsoftonline.com'
AZURE_DEFAULT_MGMT_URL = 'https://management.azure.com'
AZURE_BASE_SUBSCRIPTION_URL = 'https://management.azure.com/subscriptions?api-version'
SUBSCRIPTION_API_VERSION = '2019-11-01'

# VM ID Format: /subscriptions/[subscription-id]/resourceGroups/[resource-group-name]/providers/Microsoft.Compute/
#                virtualMachines/[virtual-machine-name]
RE_VM_RESOURCEGROUP_CG = 'resource_group'
RE_VM_RESOURCEGROUP_FROM_ID = re.compile(fr'resourceGroups\/(?P<{RE_VM_RESOURCEGROUP_CG}>[^/]+)\/providers')

# translation table between Azure VM PowerState values to parsed values, possible values retrieved from:
#   https://docs.microsoft.com/en-us/dotnet/api/microsoft.azure.management.compute.fluent.powerstate?view=azure-dotnet
POWER_STATE_MAP = {
    'PowerState/running': DeviceRunningState.TurnedOn,
    'PowerState/starting': DeviceRunningState.StartingUp,
    'PowerState/stopped': DeviceRunningState.TurnedOff,
    'PowerState/stopping': DeviceRunningState.ShuttingDown,
    'PowerState/unknown': DeviceRunningState.Unknown,

    # Special Azure VM States
    # See: https://social.msdn.microsoft.com/Forums/azure/en-US/1f608528e-a9f8-45b3-8d23-4211168cc087
    'PowerState/deallocated': DeviceRunningState.TurnedOff,
    'PowerState/deallocating': DeviceRunningState.ShuttingDown,
}
