import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from rancher_adapter.connection import RancherConnection
from rancher_adapter.client_id import get_client_id
from rancher_adapter.structures import RancherDeviceInstance, NodeCondition, \
    CustomConfig, RancherKV, NodeTaint, OwnerReference

logger = logging.getLogger(f'axonius.{__name__}')


class RancherAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(RancherDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = RancherConnection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       username=client_config['username'],
                                       password=client_config['password'])
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
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
    def _clients_schema():
        """
        The schema RancherAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Hostname or IP Address',
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
                'verify_ssl',
            ],
            'type': 'array'
        }

    @staticmethod
    def _parse_int(value):
        try:
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, bool):
            return value
        return None

    # pylint:disable=too-many-locals,too-many-branches,too-many-statements
    def _fill_rancher_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.applied_node_version = self._parse_int(device_raw.get('appliedNodeVersion'))
            device.cluster_id = device_raw.get('clusterId')

            conditions = []
            conditions_list_raw = device_raw.get('conditions')
            if isinstance(conditions_list_raw, list):
                for condition_dict in conditions_list_raw:
                    if not isinstance(condition_dict, dict):
                        logger.warning(f'Invalid condition found: {condition_dict}')
                        continue
                    try:
                        conditions.append(NodeCondition(status=condition_dict.get('status'),
                                                        type=condition_dict.get('type'),
                                                        message=condition_dict.get('message'),
                                                        reason=condition_dict.get('reason')))
                    except Exception:
                        logger.warning(f'Failed parsing condition_dict: {condition_dict}', exc_info=True)
                        # fallthrough
            if conditions:
                device.conditions = conditions

            device.control_plane = self._parse_bool(device_raw.get('controlPlane'))
            device.creator_id = device_raw.get('creatorId')

            custom_config = device_raw.get('customConfig')
            if isinstance(custom_config, dict):
                # remove sensitive data from raw
                custom_config.pop('sshKey', None)

                taints = custom_config.get('taints')
                if not (isinstance(taints, list) and taints):
                    taints = None
                try:
                    device.custom_config = CustomConfig(address=custom_config.get('address'),
                                                        docker_socket=custom_config.get('dockerSocket'),
                                                        internal_address=custom_config.get('internalAddress'),
                                                        labels=self._parse_rancher_map(custom_config.get('label')),
                                                        ssh_cert=custom_config.get('sshCert'),
                                                        taints=taints,
                                                        user=custom_config.get('user'))
                except Exception:
                    logger.warning(f'Failed parsing custom_config: {custom_config}', exc_info=True)
                    # fallthrough

            device.etcd = self._parse_bool(device_raw.get('etcd'))
            device.imported = self._parse_bool(device_raw.get('imported'))
            device.removed = parse_date(device_raw.get('removed'))
            device.namespace_id = device_raw.get('namespace_id')
            device.node_pool_id = device_raw.get('nodePoolId')
            device.node_template_id = device_raw.get('nodeTemplateId')
            device.requested_hostname = device_raw.get('requestedHostname')
            device.state = device_raw.get('state')

            transitioning = device_raw.get('transitioning')
            try:
                device.transitioning = transitioning
            except Exception:
                logger.warning(f'Unexpected transitioning value: {transitioning}')
                # fallthrough
            device.transitioning_message = device_raw.get('transitioningMessage')

            device.unschedulable = self._parse_bool(device_raw.get('unschedulable'))

            volumes_attached = device_raw.get('volumesAttached')
            if isinstance(volumes_attached, dict) and volumes_attached:
                # volumesAttached is only {'volume_name': {'name':'volume_name'}}, we take 'volume_name's.
                device.volumes_in_use = list(volumes_attached.keys())

            volumes_in_use = device_raw.get('volumesInUse')
            if isinstance(volumes_in_use, list) and volumes_in_use:
                device.volumes_in_use = volumes_in_use

            device.worker = self._parse_bool(device_raw.get('worker'))
            device.annotations = self._parse_rancher_map(device_raw.get('annotations'))
            device.rancher_labels = self._parse_rancher_map(device_raw.get('labels'))
            device.allocatable = self._parse_rancher_map(device_raw.get('allocatable'))
            device.capacity = self._parse_rancher_map(device_raw.get('capacity'))
            device.node_taints = self._parse_rancher_taints(device_raw.get('nodeTaints'))

            owner_references = []
            owner_references_raw = device_raw.get('ownerReferences')
            if isinstance(owner_references_raw, list):
                for owner_reference in owner_references_raw:
                    if not isinstance(owner_reference, dict):
                        logger.warning(f'Invalid owner reference found: {owner_reference}')
                        continue
                    try:
                        owner_references.append(OwnerReference(api_version=owner_reference.get('apiVersion'),
                                                               block_deletion=owner_reference.get('blockOwnerDeletion'),
                                                               controller=owner_reference.get('controller'),
                                                               kind=owner_reference.get('kind'),
                                                               name=owner_reference.get('name'),
                                                               uid=owner_reference.get('uid')))
                    except Exception:
                        logger.warning(f'Failed parsing owner_reference: {owner_reference}', exc_info=True)
                        # fallthrough

                if owner_references:
                    device.owner_references = owner_references

            pod_cidrs = []
            if isinstance(device_raw.get('podCidrs'), list):
                pod_cidrs.extend(device_raw.get('podCidrs'))
            if isinstance(device_raw.get('podCidr'), str):
                pod_cidrs.append(device_raw.get('podCidr'))
            if pod_cidrs:
                device.pod_cidrs = pod_cidrs

            provider_id = device_raw.get('providerId')
            if isinstance(provider_id, str):
                device.provider_id = provider_id

            device.requested = self._parse_rancher_map(device_raw.get('requested'))
            device.ssh_user = device_raw.get('sshUser')
            device.taints = self._parse_rancher_taints(device_raw.get('taints'))
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    @staticmethod
    def _parse_rancher_map(labels_raw_dict):
        keyvalues = []
        if isinstance(labels_raw_dict, dict):
            for k, v in labels_raw_dict.items():
                try:
                    keyvalues.append(RancherKV(key=k, value=v))
                except Exception:
                    logger.warning(f'Failed parsing map pair: {k} {v}', exc_info=True)
                    # fallthrough
        if not keyvalues:
            return None
        return keyvalues

    @staticmethod
    def _parse_rancher_taints(taints_raw_list):
        keyvalues = []
        if isinstance(taints_raw_list, list):
            for taint_dict in taints_raw_list:
                if not isinstance(taint_dict, dict):
                    logger.debug(f'Invalid taint_dict found: {taint_dict}')
                    continue
                try:
                    keyvalues.append(NodeTaint(key=taint_dict.get('key'),
                                               value=taint_dict.get('value'),
                                               effect=taint_dict.get('effect'),
                                               time_added=parse_date(taint_dict.get('timeAdded'))))
                except Exception:
                    logger.warning(f'Failed parsing node taint: {taint_dict}', exc_info=True)
                    # fallthrough
        if not keyvalues:
            return None

        return keyvalues

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            hostname = device_raw.get('hostname')
            ip_address = device_raw.get('ipAddress')
            device.id = f'{device_id}_{hostname or ""}_{ip_address or ""}'

            device.name = device_raw.get('nodeName') or device_raw.get('name')
            device.hostname = hostname or device_raw.get('requestedHostname')
            device.first_seen = parse_date(device_raw.get('created') or device_raw.get('createdTS'))
            device.description = device_raw.get('description')
            device.uuid = device_raw.get('uuid')

            node_info = device_raw.get('info')
            if isinstance(node_info, dict):
                cpu_info = node_info.get('cpu')
                if isinstance(cpu_info, dict):
                    device.add_cpu(cores=self._parse_int(cpu_info.get('count')))
                k8s_info = node_info.get('kubernetes')
                if not isinstance(k8s_info, dict):
                    k8s_info = {}
                os_info = node_info.get('os')
                if not isinstance(os_info, dict):
                    os_info = {}
                softwares = {'kubelet': k8s_info.get('kubeletVersion'),
                             'kube-proxy': k8s_info.get('kubeProxyVersion'),
                             'docker': os_info.get('dockerVersion')}
                for name, version in softwares.items():
                    if isinstance(version, str) and version:
                        device.add_installed_software(name=name,
                                                      version=version)
                try:
                    device.figure_os(os_info.get('operatingSystem'))
                    kernel_version = os_info.get('kernelVersion')
                    if isinstance(kernel_version, str) and kernel_version:
                        # Note: this may raise if device.os was not set in figure_os, it's ok.
                        device.os.kernel_version = kernel_version
                except Exception:
                    logger.warning(f'Failed setting os/kernel: {os_info}', exc_info=True)

                device_memory = device_raw.get('memory')
                if isinstance(device_memory, dict):
                    mem_total_kb = device_memory.get('memTotalKiB')
                    if isinstance(mem_total_kb, (int, float)):
                        device.total_physical_memory = mem_total_kb / 1024.0 / 1024.0  # kb -> gb

            ips = set()
            if isinstance(ip_address, str):
                ips.add(device_raw.get('ipAddress'))
            if isinstance(device_raw.get('externalIpAddress'), str):
                ips.add(device_raw.get('externalIpAddress'))
                device.add_public_ip(device_raw.get('externalIpAddress'))
            device.add_nic(ips=list(ips))

            self._fill_rancher_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching Rancher Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Rancher Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Virtualization, AdapterProperty.Manager]
