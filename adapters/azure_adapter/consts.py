import re

from axonius.devices.device_adapter import DeviceRunningState

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
