DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000
# Note! After this time the process will be terminated. We shouldn't ever
# terminate a process while it runs, in case its the execution we might leave
# some files on the target machine which is a bad idea. For exactly this reason
# we have another mechanism to reject execution promises on the
# execution-requester side. This value should be for times we are really really
# sure there is a problem.
MAX_SUBPROCESS_TIMEOUT = 60 * 60
WMI_NAMESPACE = '//./root/cimv2'

AUTO_BALANCER_MODE = {
    0: 'CLUSTER_AUTO_BALANCER_DISABLE',
    1: 'CLUSTER_AUTO_BALANCER_NODEUP',
    2: 'CLUSTER_AUTO_BALANCER_ALWAYS'
}

CLUSTER_LOG_LEVEL = {
    0: 'Trace',
    1: 'Debug',
    2: 'Information',
    3: 'Warning',
    4: 'Error',
    5: 'Critical',
    6: 'None'
}

DB_RW_MODE = {
    0: 'Everybody',
    1: 'MajorityWriteMajorityRead',
    2: 'MajorityWriteLocalRead'
}

DEFAULT_NETWORK_ROLE = {
    0: 'ClusterNetworkRoleNone',
    1: 'ClusterNetworkRoleInternalUse',
    2: 'ClusterNetworkRoleClientAccess',
    3: 'ClusterNetworkRoleInternalAndClient'
}

HANG_RECOVERY_ACTION = {
    0: 'WatchdogActionDisable',
    1: 'WatchdogActionLog',
    2: 'WatchdogActionTerminateProcess',
    3: 'WatchdogActionBugCheckOnlyFromNetFt',
    4: 'WatchdogActionBugCheckAlsoFromProcess',
    5: 'WatchdogActionDebugBreak',
    6: 'WatchdogActionLiveDumpAndTerminateProcess'
}

S2D_CACHE_BEHAVIOR = {
    0: 'Default',
    1: 'Dormant',
    2: 'Remove Spindle Partitions on Disable',
    3: 'Disable and Remove Flash Partitions'
}

S2D_CACHE_DESIRED_STATE = {
    0: 'Disabled',
    1: 'Read-Only',
    2: 'Read/Write',
    10: 'Provisioning',
    15: 'Provisioning - NVM Express (NVMe) Flash Tier',
    20: 'Provisioning - Spinning Media',
    120: 'Disabling',
    200: 'Dormant',
    1001: 'Ineligible - No Disks',
    1002: 'Ineligible - No NVMe Flash Tier',
    1003: 'Ineligible - Not Mixed',
}

AUTO_FAILBACK_TYPE = {
    0: 'ClusterGroupPreventFailback',
    1: 'ClusterGroupAllowFailback'
}

COLD_START_SETTING = {
    0: 'CLUS_GROUP_START_ALWAYS',
    1: 'CLUS_GROUP_DO_NOT_START',
    2: 'CLUS_GROUP_START_ALLOWED'
}

GROUP_TYPE = {
    100: 'File Server',
    101: 'Print Server',
    102: 'DHCP Server',
    103: 'Distributed Transaction Coordinator',
    104: 'Message Queing Server',
    105: 'Windows Internet Name Service',
    106: 'Stand-Along Distributed Files System',
    107: 'Generic Application',
    108: 'Generic Service',
    109: 'Generic Script',
    110: 'Internet Small Computer System Interface',
    111: 'Virtual Machine',
    112: 'Terminal Services Session Broker',
    999: 'Unknown'
}

DRAIN_STATUS = {
    0: 'NodeDrainStatusNotInitiated',
    1: 'NodeDrainStatusInProgress',
    2: 'NodeDrainStatusCompleted',
    3: 'NodeDrainStatusFailed'
}

RESTART_ACTION = {
    0: 'ClusterResourceDontRestart',
    1: 'ClusterResourceRestartNoNotify',
    2: 'ClusterResourceRestartNotify'
}
