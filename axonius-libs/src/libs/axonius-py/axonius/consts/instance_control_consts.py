from pathlib import Path

HOSTNAME_FILE_PATH = Path('/home/axonius/app/hostname')
UPLOAD_FILE_PATH = Path('/home/ubuntu/cortex/uploaded_files')
UPLOAD_FILE_SCRIPTS_PATH = Path('/home/ubuntu/cortex/devops/scripts/offline')
UPLOAD_FILE_SCRIPT_NAME = 'execute_configuration_script.py'


class InstanceControlConsts:
    DescribeClusterEndpoint = 'describe_cluster'
    EnterUpgradeModeEndpoint = 'enter_upgrade_mode'
    PullUpgrade = 'pull_upgrade'
    TriggerUpgrade = 'trigger_upgrade'
    FileExecute = 'file_execute'
