import logging
import os
import re

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none

from failover_cluster_adapter.client_id import get_client_id
from failover_cluster_adapter.connection import FailoverClusterConnection
from failover_cluster_adapter.consts import AUTO_BALANCER_MODE, \
    CLUSTER_LOG_LEVEL, DB_RW_MODE, DEFAULT_NETWORK_ROLE, HANG_RECOVERY_ACTION, \
    S2D_CACHE_DESIRED_STATE, AUTO_FAILBACK_TYPE, COLD_START_SETTING, \
    GROUP_TYPE, DRAIN_STATUS, RESTART_ACTION
from failover_cluster_adapter.structures import FailoverClusterNodeInstance, \
    FailoverCluster, FailoverClusterOwnerGroup, FailoverClusterOwnerNode, \
    FailoverClusterResourceType

logger = logging.getLogger(f'axonius.{__name__}')


class FailoverClusterAdapter(AdapterBase):
    class MyDeviceAdapter(FailoverClusterNodeInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__),
                         *args,
                         **kwargs)

    @property
    def _use_wmi_smb_path(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            self.config['paths']['wmi_smb_path']))

    @property
    def _python_27_path(self):
        return self.config['paths']['python_27_path']

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    def get_connection(self, client_config):
        connection = FailoverClusterConnection(domain=client_config['domain'],
                                               username=client_config['username'],
                                               password=client_config['password'],
                                               wmi_util_path=self._use_wmi_smb_path,
                                               python_path=self._python_27_path,
                                               verify_ssl=client_config['verify_ssl'],
                                               https_proxy=client_config.get('https_proxy'),
                                               )
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = f'Error connecting to client with domain ' \
                      f'{client_config.get("domain")}, reason: {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema() -> dict:
        """
        The schema FailoverClusterAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Failover Cluster Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _parse_cluster_configuration(config: dict) -> FailoverCluster:
        # extract the epoch time from a string that looks like:
        #   '/Date(1596586718242)/'
        reset_time = config.get('RecentEventsResetTime')
        if reset_time and isinstance(reset_time, str):
            recent_events_reset_time = int_or_none(re.search(r'\(([^)]+)', reset_time).group(1))
        else:
            recent_events_reset_time = None

        cluster_configuration = FailoverCluster(
            add_evict_delay=int_or_none(config.get('AddEvictDelay')),
            administrative_access_point=int_or_none(config.get('AdministrativeAccessPoint')),
            auto_assign_node_site=int_or_none(config.get('AutoAssignNodeSite')),
            auto_balancer_level=int_or_none(config.get('AutoBalancerLevel')),
            auto_balancer_mode=AUTO_BALANCER_MODE.get(int_or_none(config.get('AutoBalancerMode'))),
            backup_in_progress=parse_bool_from_raw(config.get('BackupInProgress')),
            block_cache_size=int_or_none(config.get('BlockCacheSize')),
            clus_svc_hang_timeout=int_or_none(config.get('ClusSvcHangTimeout')),
            clus_svc_regroup_stage_timeout=int_or_none(config.get('ClusSvcRegroupStageTimeout')),
            clus_svc_regroup_tick_in_ms=int_or_none(config.get('ClusSvcRegroupTickInMilliseconds')),
            cluster_enforced_anti_affinity=parse_bool_from_raw(
                config.get('ClusterEnforcedAntiAffinity')
            ),
            cluster_functional_level=int_or_none(config.get('ClusterFunctionalLevel')),
            cluster_upgrade_version=int_or_none(config.get('ClusterUpgradeVersion')),
            cluster_group_wait_delay=int_or_none(config.get('ClusterGroupWaitDelay')),
            cluster_log_level=CLUSTER_LOG_LEVEL.get(int_or_none(config.get('ClusterLogLevel'))),
            cluster_log_size=int_or_none(config.get('ClusterLogSize')),
            cross_site_delay=int_or_none(config.get('CrossSiteDelay')),
            cross_site_threshold=int_or_none(config.get('CrossSiteThreshold')),
            cross_subnet_delay=int_or_none(config.get('CrossSubnetDelay')),
            cross_subnet_threshold=int_or_none(config.get('CrossSubnetThreshold')),
            csv_balancer=int_or_none(config.get('CsvBalancer')),
            database_read_write_mode=DB_RW_MODE.get(int_or_none(
                config.get('DatabaseReadWriteMode'))),
            default_network_role=DEFAULT_NETWORK_ROLE.get(int_or_none(
                config.get('DefaultNetworkRole'))),
            description=config.get('Description'),
            domain=config.get('Domain'),
            drain_on_shutdown=parse_bool_from_raw(config.get('DrainOnShutdown')),
            dump_policy=int_or_none(config.get('DumpPolicy')),
            dynamic_quorum=parse_bool_from_raw(config.get('DynamicQuorum')),
            enable_shared_volumes=parse_bool_from_raw(config.get('EnableSharedVolumes')),
            fix_quorum=parse_bool_from_raw(config.get('FixQuorum')),
            group_dependency_timeout=int_or_none(config.get('GroupDependencyTimeout')),
            hang_recovery_action=HANG_RECOVERY_ACTION.get(int_or_none(
                config.get('HangRecoveryAction'))),
            id=config.get('Id'),
            ignore_persistent_state_on_startup=parse_bool_from_raw(
                config.get('IgnorePersistentStateOnStartup')),
            log_resource_controls=parse_bool_from_raw(config.get('LogResourceControls')),
            lower_quorum_priority_node_id=int_or_none(config.get('LowerQuorumPriorityNodeId')),
            message_buffer_length=int_or_none(config.get('MessageBufferLength')),
            min_never_preempt_priority=int_or_none(config.get('MinimumNeverPreemptPriority')),
            min_preempt_priority=int_or_none(config.get('MinimumPreemptorPriority')),
            name=config.get('Name'),
            netft_ipsec_enabled=parse_bool_from_raw(config.get('NetftIPSecEnabled')),
            placement_options=int_or_none(config.get('PlacementOptions')),
            plumb_all_cross_subnet_routes=int_or_none(config.get('PlumbAllCrossSubnetRoutes')),
            preferred_site=config.get('PreferredSite'),
            prevent_quorum=parse_bool_from_raw(config.get('PreventQuorum')),
            quarantine_duration=int_or_none(config.get('QuarantineDuration')),
            quarantine_threshold=int_or_none(config.get('QuarantineThreshold')),
            quorum_arbitration_time_max=int_or_none(config.get('QuorumArbitrationTimeMax')),
            recent_events_reset_time=parse_date(recent_events_reset_time),
            request_reply_timeout=int_or_none(config.get('RequestReplyTimeout')),
            resiliency_default_period=int_or_none(config.get('ResiliencyDefaultPeriod')),
            resiliency_level=int_or_none(config.get('ResiliencyLevel')),
            route_history_length=int_or_none(config.get('RouteHistoryLength')),
            s2d_bus_types=int_or_none(config.get('S2DBusTypes')),
            s2d_cache_behavior=config.get('S2DCacheBehavior'),
            s2d_cache_desired_state=S2D_CACHE_DESIRED_STATE.get(
                int_or_none(config.get('S2DCacheDesiredState'))),
            s2d_cache_metadata_reserve_bytes=int_or_none(
                config.get('S2DCacheMetadataReserveBytes')),
            s2d_cache_page_size_kb=int_or_none(config.get('S2DCachePageSizeKBytes')),
            s2d_enabled=parse_bool_from_raw(config.get('S2DEnabled')),
            s2d_io_latency_threshold=int_or_none(config.get('S2DIOLatencyThreshold')),
            s2d_optimizations=int_or_none(config.get('S2DOptimizations')),
            same_subnet_delay=int_or_none(config.get('SameSubnetDelay')),
            same_subnet_threshold=int_or_none(config.get('SameSubnetThreshold')),
            security_level=int_or_none(config.get('SecurityLevel')),
            shared_volume_compatible_filters=config.get('SharedVolumeCompatibleFilters'),
            shared_volume_incompatible_filters=config.get('SharedVolumeIncompatibleFilters'),
            shared_volume_security_descriptor=config.get('SharedVolumeSecurityDescriptor'),
            shared_volume_vss_writer_operation_timeout=int_or_none(
                config.get('SharedVolumeVssWriterOperationTimeout')),
            shared_volumes_root=config.get('SharedVolumesRoot'),
            shutdown_timeout_in_minutes=int_or_none(config.get('ShutdownTimeoutInMinutes')),
            use_client_access_networks_for_shared_volumes=int_or_none(
                config.get('UseClientAccessNetworksForSharedVolumes')),
            witness_database_write_timeout=int_or_none(config.get('WitnessDatabaseWriteTimeout')),
            witness_dynamic_weight=int_or_none(config.get('WitnessDynamicWeight')),
            witness_restart_interval=int_or_none(config.get('WitnessRestartInterval'))
        )
        return cluster_configuration

    @staticmethod
    def _parse_owner_group(config: dict) -> FailoverClusterOwnerGroup:
        owner_group = FailoverClusterOwnerGroup(
            anti_affinity_class_names=config.get('AntiAffinityClassNames'),
            auto_failback_type=AUTO_FAILBACK_TYPE.get(int_or_none(
                config.get('AutoFailbackType'))),
            cold_start_setting=COLD_START_SETTING.get(int_or_none(
                config.get('ColdStartSetting'))),
            cluster=config.get('Cluster'),
            default_owner=int_or_none(config.get('DefaultOwner')),
            description=config.get('Description'),
            group_type=GROUP_TYPE.get(int_or_none(config.get('GroupType'))),
            failover_period=int_or_none(config.get('FailoverPeriod')),
            failover_threshold=int_or_none(config.get('FailoverThreshold')),
            failback_window_end=int_or_none(config.get('FailbackWindowEnd')),
            failback_window_start=int_or_none(config.get('FailbackWindowStart')),
            fault_domain=int_or_none(config.get('FaultDomain')),
            is_core_group=parse_bool_from_raw(config.get('IsCoreGroup')),
            name=config.get('Name'),
            owner_node=config.get('OwnerNode'),
            persistent_state=parse_bool_from_raw(config.get('PersistentState')),
            preferred_site=config.get('PreferredSite'),
            priority=int_or_none(config.get('Priority')),
            resiliency_period=int_or_none(config.get('ResiliencyPeriod')),
            state=int_or_none(config.get('State')),
            status_information=config.get('StatusInformation'),
            update_domain=int_or_none(config.get('UpdateDomain')),
            id=config.get('Id')
        )
        return owner_group

    @staticmethod
    def _parse_owner_node(config: dict) -> FailoverClusterOwnerNode:
        owner_node = FailoverClusterOwnerNode(
            build_number=int_or_none(config.get('BuildNumber')),
            cluster=config.get('Cluster'),
            csd_version=config.get('CSDVersion'),
            description=config.get('Description'),
            drain_status=DRAIN_STATUS.get(int_or_none(config.get('DrainStatus'))),
            drain_target=int_or_none(config.get('DrainTarget')),
            dynamic_weight=int_or_none(config.get('DynamicWeight')),
            id=config.get('Id'),
            major_version=int_or_none(config.get('MajorVersion')),
            minor_version=int_or_none(config.get('MinorVersion')),
            name=config.get('Name'),
            needs_prevent_quorum=int_or_none(config.get('NeedsPreventQuorum')),
            node_highest_version=int_or_none(config.get('NodeHighestVersion')),
            node_instance_id=config.get('NodeInstanceID'),
            node_lowest_version=int_or_none(config.get('NodeLowestVersion')),
            node_name=config.get('NodeName'),
            node_weight=int_or_none(config.get('NodeWeight')),
            fault_domain=config.get('FaultDomain'),
            model=config.get('Model'),
            manufacturer=config.get('Manufacturer'),
            serial_number=config.get('SerialNumber'),
            state=int_or_none(config.get('State')),
            status_information=int_or_none(config.get('StatusInformation'))
        )
        return owner_node

    @staticmethod
    def _parse_resource_type(config: dict) -> FailoverClusterResourceType:
        resource_type = FailoverClusterResourceType(
            admin_extensions=config.get('AdminExtensions'),
            characteristics=int_or_none(config.get('Characteristics')),
            cluster=config.get('Cluster'),
            deadlock_timeout=int_or_none(config.get('DeadlockTimeout')),
            description=config.get('Description'),
            display_name=config.get('DisplayName'),
            dll_name=config.get('DllName'),
            dump_log_query=config.get('DumpLogQuery'),
            dump_policy=int_or_none(config.get('DumpPolicy')),
            dump_services=config.get('DumpServices'),
            enabled_event_logs=config.get('EnabledEventLogs'),
            id=config.get('Id'),
            is_alive_poll_interval=int_or_none(config.get('IsAlivePollInterval')),
            looks_alive_poll_interval=int_or_none(config.get('LooksAlivePollInterval')),
            maximum_monitors=int_or_none(config.get('MaximumMonitors')),
            name=config.get('Name'),
            pending_timeout=int_or_none(config.get('PendingTimeout'))
        )
        return resource_type

    # pylint: disable=too-many-statements
    def _fill_failover_cluster_device_fields(self,
                                             device_raw: dict,
                                             device: MyDeviceAdapter):
        try:
            cluster_configuration = self._parse_cluster_configuration(
                config=device_raw.get('Cluster')
            )
        except Exception as err:
            logger.exception(f'Unable to parse the cluster configuration: '
                             f'{str(err)}')
            cluster_configuration = None

        try:
            owner_group = self._parse_owner_group(config=device_raw.get('OwnerGroup'))
        except Exception as err:
            logger.exception(f'Unable to parse owner group: {str(err)}')
            owner_group = None

        try:
            owner_node = self._parse_owner_node(config=device_raw.get('OwnerNode'))
        except Exception as err:
            logger.exception(f'Unable to parse owner node: {str(err)}')
            owner_node = None

        try:
            resource_type = self._parse_resource_type(config=device_raw.get('ResourceType'))
        except Exception as err:
            logger.exception(f'Unable to parse resource type: {str(err)}')
            resource_type = None

        try:
            device.characteristics = int_or_none(device_raw.get('Characteristics'))
            device.cluster_configuration = cluster_configuration
            device.deadlock_timeout = int_or_none(device_raw.get('DeadlockTimeout'))
            device.is_core_resource = parse_bool_from_raw(device_raw.get('IsCoreResource'))
            device.embedded_failure_action = int_or_none(device_raw.get('EmbeddedFailureAction'))
            device.is_alive_poll_interval = int_or_none(device_raw.get('IsAlivePollInterval'))
            device.is_network_class_resource = parse_bool_from_raw(
                device_raw.get('IsAlivePollInterval')
            )
            device.is_storage_class_resource = parse_bool_from_raw(
                device_raw.get('IsStorageClassResource')
            )
            device.last_operation_status_code = int_or_none(
                device_raw.get('LastOperationStatusCode')
            )
            device.looks_alive_poll_interval = int_or_none(
                device_raw.get('LooksAlivePollInterval')
            )
            device.maintenance_mode = parse_bool_from_raw(device_raw.get('MaintenanceMode'))
            device.monitor_process_id = int_or_none(device_raw.get('MonitorProcessId'))
            device.owner_group = owner_group
            device.owner_node = owner_node
            device.pending_timeout = int_or_none(device_raw.get('PendingTimeout'))
            device.persistent_state = parse_bool_from_raw(device_raw.get('PersistentState'))
            device.resource_specific_data_1 = int_or_none(device_raw.get('ResourceSpecificData1'))
            device.resource_specific_data_2 = int_or_none(device_raw.get('ResourceSpecificData2'))
            device.resource_specific_status = int_or_none(device_raw.get('ResourceSpecificStatus'))
            device.resource_type = resource_type
            device.restart_action = RESTART_ACTION.get(device_raw.get('RestartAction'))
            device.restart_delay = int_or_none(device_raw.get('RestartDelay'))
            device.restart_period = int_or_none(device_raw.get('RestartPeriod'))
            device.restart_threshold = int_or_none(device_raw.get('RestartThreshold'))
            device.retry_period_on_failover = int_or_none(device_raw.get('RetryPeriodOnFailure'))
            device.separate_monitor = parse_bool_from_raw(device_raw.get('SeparateMonitor'))
            device.state = int_or_none(device_raw.get('State'))
            device.status_information = int_or_none(device_raw.get('StatusInformation'))
        except Exception:
            logger.exception(f'Failed to create device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            cluster = device_raw.get('Cluster')
            if not isinstance(cluster, dict):
                logger.warning(f'Malformed cluster. Expected a dict, got '
                               f'{type(cluster)}: {str(cluster)}')
                # no valid cluster info, so bail out
                return None

            domain = cluster.get('Domain') or ''

            device_id = device_raw.get('Id')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            owner_group = device_raw.get('OwnerGroup')
            if isinstance(owner_group, dict):
                cluster_owner = owner_group.get('Cluster') or 'cluster_owner'
                if not (cluster_owner and isinstance(cluster_owner, str)):
                    logger.warning(f'Malformed cluster owner. Expected a str, '
                                   f'got {type(cluster_owner)}: {str(cluster_owner)}')
                    cluster_owner = 'cluster_owner'
            else:
                logger.warning(f'Malformed owner group. Expected a dict, got '
                               f'{type(owner_group)}: {str(owner_group)}')
                cluster_owner = 'cluster_owner'

            device.id = str(device_id) + '_' + cluster_owner + domain

            owner_node = device_raw.get('OwnerNode')
            if not isinstance(owner_node, dict):
                logger.warning(f'Malformed owner node. Expected a dict, got '
                               f'{type(owner_node)}: {str(owner_node)}')
                # no valid cluster owner info, so bail out
                return None

            device.device_manufacturer = owner_node.get('Manufacturer')
            device.device_model = owner_node.get('Model')
            device.device_serial = owner_node.get('SerialNumber')
            device.name = owner_node.get('Name')
            device.hostname = owner_node.get('Name')
            device.domain = cluster.get('Domain')
            device.description = device_raw.get('Description')

            self._fill_failover_cluster_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem parsing FailoverCluster Device: '
                             f'{device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        """
        for device_raw_data in devices_raw_data:
            if not device_raw_data:
                continue

            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw_data,
                                             self._new_device_adapter())
                if device:
                    yield device

            except Exception:
                logger.exception(f'Problem parsing FailoverCluster Device: '
                                 f'{device_raw_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Manager]
