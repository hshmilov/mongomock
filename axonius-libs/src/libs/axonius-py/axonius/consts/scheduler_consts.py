from enum import Enum, auto

from namedlist import namedlist


class Phases(Enum):
    """
    Possible phases of the system.
    Currently may be Research, meaning fetch and calculate are running, or Stable, meaning nothing is being changed.
    """
    Research = auto()
    Stable = auto()


class ResearchPhases(Enum):
    """
    Possible sub-phases of the Research phase, representing stages system goes through before completing the research.
    """
    Fetch_Devices = 'Fetch Devices'
    Fetch_Scanners = 'Fetch Scanners'
    Clean_Devices = 'Clean Devices'
    Pre_Correlation = 'Prepare Correlations'
    Run_Correlations = 'Run Correlations'
    Post_Correlation = 'Process Correlations'
    Run_Queries = 'Run Queries'
    Save_Historical = 'Save History'


SchedulerState = namedlist('SchedulerState',
                           [
                               ('SubPhase', None),
                               ('SubPhaseStatus', None),
                               ('Phase', Phases.Stable),
                               ('AssociatePluginId', None)],
                           )

RESEARCH_THREAD_ID = 'phase_thread'
CORRELATION_SCHEDULER_THREAD_ID = 'correlation_scheduler_thread'
CHECK_ADAPTER_CLIENTS_STATUS_INTERVAL = 90
TUNNEL_STATUS_CHECK_INTERVAL = 15

# Configurable
SCHEDULER_CONFIG_NAME = 'SystemSchedulerService'
SCHEDULER_SAVE_HISTORY_CONFIG_NAME = 'enabled'

CUSTOM_DISCOVERY_CHECK_INTERVAL = 90  # seconds
CUSTOM_DISCOVERY_THRESHOLD = 3 * 60  # seconds

RUN_ENFORCEMENT_CHECK_INTERVAL = 90  # seconds
RUN_ENFORCEMENT_CHECK_THRESHOLD = 180  # seconds

BACKUP_SETTINGS = 'backup_settings'


class BackupSettings:
    enabled = 'enabled'
    encryption_key = 'backup_encryption_key'
    include_history = 'include_history'
    include_devices_users_data = 'include_devices_users_data'
    override_previous_backups = 'override_previous_backups'
    min_days_between_cycles = 'min_days_between_cycles'
    backup_to_aws_s3 = 'backup_to_aws_s3'
    backup_to_smb = 'backup_to_smb'
    backup_to_azure = 'backup_to_azure'


class BackupRepoAzure:
    enabled = 'enabled'
    container_name = 'storage_container_name'
    connection_string = 'connection_string'


class BackupRepoAws:
    enabled = 'enabled'
    bucket_name = 'aws_bucket_name'
    access_key_id = 'aws_access_key_id'
    secret_access_key = 'aws_secret_access_key'


class BackupRepoSmb:
    enabled = 'enabled'
    ip = 'ip'
    port = 'port'
    path = 'smb_path'
    user = 'smb_user'
    password = 'smb_password'
    use_nbns = 'use_nbns'
    hostname = 'hostname'
