import datetime

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass


class FailoverCluster(SmartJsonClass):
    """
    Cluster Common Properties:
    https://docs.microsoft.com/en-us/previous-versions/windows/desktop/mscs/cluster-common-properties
    """
    add_evict_delay = Field(int, 'Add / Evict Delay')
    administrative_access_point = Field(int, 'Administrative Access Point')
    auto_assign_node_site = Field(int, 'Auto Assign Node Site')
    auto_balancer_level = Field(int, 'Auto Balancer Level')
    auto_balancer_mode = Field(str, 'Auto Balancer Mode')
    backup_in_progress = Field(bool, 'Backup In Progress')
    block_cache_size = Field(int, 'Block Cache Size')
    clus_svc_hang_timeout = Field(int, 'Cluster Service Hang Timeout')
    clus_svc_regroup_stage_timeout = Field(int, 'Cluster Service Regroup Stage Timeout')
    clus_svc_regroup_tick_in_ms = Field(int, 'Cluster Service Regroup Tick Timeout')
    cluster_enforced_anti_affinity = Field(bool, 'Cluster Enforced Anti-Affinity')
    cluster_functional_level = Field(int, 'Cluster Functional Level')
    cluster_upgrade_version = Field(int, 'Cluster Upgrade Version')
    cluster_group_wait_delay = Field(int, 'Cluster Group Wait Delay')
    cluster_log_level = Field(str, 'Cluster Log Level')
    cluster_log_size = Field(int, 'Cluster Log Size')
    cross_site_delay = Field(int, 'Cross-Site Delay')
    cross_site_threshold = Field(int, 'Cross-Site Threshold')
    cross_subnet_delay = Field(int, 'Cross-Subnet Delay')
    cross_subnet_threshold = Field(int, 'Cross-Subnet Threshold')
    csv_balancer = Field(int, 'Csv Balancer')
    database_read_write_mode = Field(str, 'Database Read/Write Mode')
    default_network_role = Field(str, 'Default Network Role')
    description = Field(str, 'Description')
    domain = Field(str, 'Domain')
    drain_on_shutdown = Field(bool, 'Drain on Shutdown')
    dump_policy = Field(int, 'Dump Policy')
    dynamic_quorum = Field(bool, 'Dynamic Quorum')
    enable_shared_volumes = Field(bool, 'Enable Shared Volumes')  # always True
    fix_quorum = Field(bool, 'Fix Quorum')
    group_dependency_timeout = Field(int, 'Group Dependency Timeout')
    hang_recovery_action = Field(str, 'Hang Recovery Action')
    id = Field(str, 'ID')
    ignore_persistent_state_on_startup = Field(bool, 'Ignore Persistent State on Startup')
    log_resource_controls = Field(bool, 'Log Resource Controls')
    lower_quorum_priority_node_id = Field(int, 'Lower Quorum Priority Node ID')
    message_buffer_length = Field(int, 'Message Buffer Length')
    min_never_preempt_priority = Field(int, 'Minimum Never Preempt Priority')
    min_preempt_priority = Field(int, 'Minimum Preemptor Priority')
    name = Field(str, 'Name')
    netft_ipsec_enabled = Field(bool, 'Netft IPSec Enabled')
    placement_options = Field(int, 'Placement Options')
    plumb_all_cross_subnet_routes = Field(int, 'Plumb All Cross-Subnet Routes')
    preferred_site = Field(str, 'Preferred Site')
    prevent_quorum = Field(bool, 'Prevent Quorum')
    quarantine_duration = Field(int, 'Quarantine Duration')
    quarantine_threshold = Field(int, 'Quarantine Threshold')
    quorum_arbitration_time_max = Field(int, 'Quorum Arbitration Time (Max)')
    recent_events_reset_time = Field(datetime.datetime, 'Recent Events Reset Time')
    request_reply_timeout = Field(int, 'Request Reply Timeout')
    resiliency_default_period = Field(int, 'Resiliency Default Period')
    resiliency_level = Field(int, 'Resiliency Level')
    route_history_length = Field(int, 'Route History Length')
    s2d_bus_types = Field(int, 'S2D Bus Types')
    s2d_cache_behavior = Field(str, 'S2D Cache Behavior')
    s2d_cache_desired_state = Field(str, 'S2D Cache Desired State')
    s2d_cache_metadata_reserve_bytes = Field(int, 'S2D Cache Metadata Reserve (Bytes)')
    s2d_cache_page_size_kb = Field(int, 'S2D Cache Page Size (Kb)')
    s2d_enabled = Field(bool, 'S2D Enabled')
    s2d_io_latency_threshold = Field(int, 'S2D IO Latency Threshold')
    s2d_optimizations = Field(int, 'S2D Optimizations')
    same_subnet_delay = Field(int, 'Same Subnet Delay')
    same_subnet_threshold = Field(int, 'Same Subnet Threshold')
    security_level = Field(int, 'Security Level')
    shared_volume_compatible_filters = Field(str, 'Shared Volume Compatible Filters')
    shared_volume_incompatible_filters = Field(str, 'Shared Volume Incompatible Filters')
    shared_volume_security_descriptor = Field(str, 'Shared Volume Security Descriptor')
    shared_volume_vss_writer_operation_timeout = Field(int, 'Shared Volume VSS Writer Operation Timeout')
    shared_volumes_root = Field(str, 'Shared Volumes Root')
    shutdown_timeout_in_minutes = Field(int, 'Shutdown Timeout in Minutes')
    use_client_access_networks_for_shared_volumes = Field(int, 'Use Client Access Networks for Shared Volumes')
    witness_database_write_timeout = Field(int, 'Witness DB Write Timeout')
    witness_dynamic_weight = Field(int, 'Witness Dynamic Weight')
    witness_restart_interval = Field(int, 'Witness Restart Interval')


class FailoverClusterOwnerGroup(SmartJsonClass):
    """
    Cluster Group Common Data:
    https://docs.microsoft.com/en-us/previous-versions/windows/desktop/mscs/group-common-properties

    Status Information:
    # https://docs.microsoft.com/en-us/previous-versions/windows/desktop/mscs/groups-statusinformation
    """
    anti_affinity_class_names = Field(str, 'Anti-Affinity Class Names')
    auto_failback_type = Field(str, 'Auto-Failback Type')
    cold_start_setting = Field(str, 'Cold Start Setting')
    cluster = Field(str, 'Cluster')
    default_owner = Field(int, 'Default Owner')
    description = Field(str, 'Description')
    group_type = Field(str, 'Group Type')
    failover_period = Field(int, 'Failover Period')
    failover_threshold = Field(int, 'Failover Threshold')
    failback_window_end = Field(int, 'Failback Window End')
    failback_window_start = Field(int, 'Failback Window Start')
    fault_domain = Field(int, 'Fault Domain')
    is_core_group = Field(bool, 'Is Core Group')
    name = Field(str, 'Name')
    owner_node = Field(str, 'Owner Node')
    persistent_state = Field(bool, 'Persistent State')
    preferred_site = Field(str, 'Preferred Site')
    priority = Field(int, 'Priority')
    resiliency_period = Field(int, 'Resiliency Period')
    state = Field(int, 'State')
    status_information = Field(str, 'Status Information')
    update_domain = Field(int, 'Update Domain')
    id = Field(str, 'ID')


class FailoverClusterOwnerNode(SmartJsonClass):
    """
    Node Common Properties:
    https://docs.microsoft.com/en-us/previous-versions/windows/desktop/mscs/node-common-properties

    Status Information:
    https://docs.microsoft.com/en-us/previous-versions/windows/desktop/mscs/resources-statusinformation
    """
    build_number = Field(int, 'Build Number')
    cluster = Field(str, 'Cluster')
    csd_version = Field(str, 'CSD Version')
    description = Field(str, 'Description')
    drain_status = Field(str, 'Drain Status')
    drain_target = Field(int, 'Drain Target')
    dynamic_weight = Field(int, 'Dynamic Weight')
    id = Field(str, 'ID')
    major_version = Field(int, 'Major Version')
    minor_version = Field(int, 'Minor Version')
    name = Field(str, 'Name')
    needs_prevent_quorum = Field(int, 'Needs Prevent Quorum')
    node_highest_version = Field(int, 'Node Highest Version')
    node_instance_id = Field(str, 'Node Instance ID')
    node_lowest_version = Field(int, 'Node Lowest Version')
    node_name = Field(str, 'Node Name')
    node_weight = Field(int, 'Node Weight')
    fault_domain = Field(str, 'Fault Domain')
    model = Field(str, 'Model')
    manufacturer = Field(str, 'Manufacturer')
    serial_number = Field(str, 'Serial Number')
    state = Field(int, 'State')
    status_information = Field(int, 'Status Information')


class FailoverClusterResourceType(SmartJsonClass):
    """
    Resource Type Common Properties:
    https://docs.microsoft.com/en-us/previous-versions/windows/desktop/mscs/resource-type-common-properties
    """
    admin_extensions = Field(str, 'Admin Extensions')
    characteristics = Field(int, 'Characteristics')
    cluster = Field(str, 'Cluster')
    deadlock_timeout = Field(int, 'Deadlock Timeout')
    description = Field(str, 'Description')
    display_name = Field(str, 'Display Name')
    dll_name = Field(str, 'DLL Name')
    dump_log_query = Field(str, 'Dump Log Query')
    dump_policy = Field(int, 'Dump Policy')
    dump_services = Field(str, 'Dump Services')  # docs aren't clear
    enabled_event_logs = Field(str, 'Enabled Event Logs')  # docs aren't clear
    id = Field(str, 'ID')  # docs aren't clear
    is_alive_poll_interval = Field(int, 'Is Alive Poll Interval')
    looks_alive_poll_interval = Field(int, 'Looks Alive Poll Interval')
    maximum_monitors = Field(int, 'Maximum Monitors')
    name = Field(str, 'Name')
    pending_timeout = Field(int, 'Pending Timeout')


class FailoverClusterNodeInstance(DeviceAdapter):
    characteristics = Field(int, 'Characteristics')
    cluster_configuration = Field(FailoverCluster, 'Cluster Configuration')
    deadlock_timeout = Field(int, 'Deadlock Timeout')
    is_core_resource = Field(bool, 'Is Core Resource')
    embedded_failure_action = Field(int, 'Embedded Failure Action')
    is_alive_poll_interval = Field(int, 'Is Alive Poll Interval')
    is_network_class_resource = Field(bool, 'Is Network Class Resource')
    is_storage_class_resource = Field(bool, 'Is Storage Class Resource')
    last_operation_status_code = Field(int, 'Last Operation Status Code')
    looks_alive_poll_interval = Field(int, 'Looks Alive Poll Interval')
    maintenance_mode = Field(bool, 'Maintenance Mode')
    monitor_process_id = Field(int, 'Monitor Process ID')
    owner_group = Field(FailoverClusterOwnerGroup, 'Owner Group')
    owner_node = Field(FailoverClusterOwnerNode, 'Owner Node')
    pending_timeout = Field(int, 'Pending Timeout')
    persistent_state = Field(bool, 'Persistent State')  # docs aren't clear
    resource_specific_data_1 = Field(int, 'Resource Specific Data 1')
    resource_specific_data_2 = Field(int, 'Resource Specific Data 2')
    resource_specific_status = Field(int, 'Resource Specific Status')  # docs aren't clear
    resource_type = Field(FailoverClusterResourceType, 'Resource Type')
    restart_action = Field(str, 'Restart Action')
    restart_delay = Field(int, 'Restart Delay')
    restart_period = Field(int, 'Restart Period')
    restart_threshold = Field(int, 'Restart Threshold')
    retry_period_on_failover = Field(int, 'Retry Period On Failure')
    separate_monitor = Field(bool, 'Separate Monitor')
    state = Field(int, 'State')
    status_information = Field(int, 'Status Information')
