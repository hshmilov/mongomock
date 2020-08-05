from pathlib import Path

from axonius.consts.plugin_consts import BOOT_CONFIGURATION_SCRIPT_FILENAME

HOSTNAME_FILE_PATH = Path('/home/axonius/app/hostname')
UPLOAD_FILE_PATH = Path('/home/axonius/uploaded_files')
UPLOAD_FILE_SCRIPTS_PATH = Path('/home/ubuntu/cortex/devops/scripts/offline')
UPLOAD_FILE_SCRIPT_NAME = 'execute_configuration_script.py'
BOOT_CONFIG_FILE_PATH = Path(UPLOAD_FILE_PATH, BOOT_CONFIGURATION_SCRIPT_FILENAME)


class InstanceControlConsts:
    DescribeClusterEndpoint = 'describe_cluster'
    EnterUpgradeModeEndpoint = 'enter_upgrade_mode'
    PullUpgrade = 'pull_upgrade'
    TriggerUpgrade = 'trigger_upgrade'
    FileExecute = 'file_execute'


class MetricsFields:
    Ips = 'ips'
    CpuUsage = 'cpu_usage'
    MemoryFreeSpace = 'memory_free_space'
    MemorySize = 'memory_size'
    SwapSize = 'swap_size'
    SwapFreeSpace = 'swap_free_space'
    SwapCacheSize = 'swap_cache_size'
    DataDiskFreeSpace = 'data_disk_free_space'
    DataDiskSize = 'data_disk_size'
    OsDiskFreeSpace = 'os_disk_free_space'
    OsDiskSize = 'os_disk_size'
    PhysicalCpu = 'physical_cpu'
    CpuCores = 'cpu_cores'
    CpuCoreThreads = 'cpu_core_threads'
    LastSnapshotSize = 'last_snapshot_size'
    MaxSnapshots = 'max_snapshots'
    RemainingSnapshotDays = 'remaining_snapshots_days'
    LastUpdated = 'last_updated'


METRICS_INTERVAL_MINUTES = 10


METRICS_SCRIPT_PATH = '/home/ubuntu/cortex/plugins/instance_control/get_instance_metrics.py'
METRICS_ENV_FILE_PATH = '/home/ubuntu/cortex/prepare_python_env.sh'
