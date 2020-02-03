from pathlib import Path

HOSTNAME_FILE_PATH = Path('/home/axonius/app/hostname')


class InstanceControlConsts:
    DescribeClusterEndpoint = 'describe_cluster'
    EnterUpgradeModeEndpoint = 'enter_upgrade_mode'
    PullUpgrade = 'pull_upgrade'
    TriggerUpgrade = 'trigger_upgrade'
