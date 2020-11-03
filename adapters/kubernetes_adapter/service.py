import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.kubernetes.connection import KubernetesConnection
from axonius.clients.kubernetes.consts import DEFAULT_PORT
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from kubernetes_adapter.client_id import get_client_id
from kubernetes_adapter.structures import KubernetesDeviceInstance, get_value_or_default

logger = logging.getLogger(f'axonius.{__name__}')


class KubernetesAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(KubernetesDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(
            client_config.get('domain'),
            port=client_config.get('port', DEFAULT_PORT)
        )

    @staticmethod
    def get_connection(client_config):
        with KubernetesConnection(
                token=client_config.get('token'),
                domain=client_config.get('domain'),
                port=client_config.get('port'),
                verify_ssl=client_config.get('verify_ssl')
        ) as connection:  # check that the connection credentials are valid
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
        Get all devices from a specific domain
        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection
        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema KubernetesAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'format': 'port',
                    'default': DEFAULT_PORT
                },
                {
                    'name': 'token',
                    'title': 'Token',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'port',
                'token',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-statements
    @staticmethod
    def _fill_kubernetes_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            meta_data = get_value_or_default('meta_data', device_raw.get('metadata'), dict)
            spec = get_value_or_default('spec', device_raw.get('spec'), dict)
            status = get_value_or_default('status', device_raw.get('status'), dict)
            container = get_value_or_default('container', device_raw.get('container'), dict)
            labels = get_value_or_default('labels', meta_data.get('labels'), dict)
            volume_mounts = get_value_or_default('volume_mounts', container.get('volume_mounts'), list)
            owner_references = get_value_or_default('owner_references', meta_data.get('owner_references'), list)

            device.cluster_name = meta_data.get('cluster_name')
            device.pod_name = meta_data.get('name')
            device.pod_uid = meta_data.get('uid')
            device.pod_generate_name = meta_data.get('generate_name')
            device.namespace = meta_data.get('namespace')
            device.resource_version = meta_data.get('resource_version')
            device.pod_link = meta_data.get('self_link')
            device.termination_grace_period = int_or_none(meta_data.get('termination_grace_period'))
            device.node_name = spec.get('node_name')
            device.dns_policy = spec.get('dns_policy')
            device.priority = int_or_none(spec.get('priority'))
            device.restart_policy = spec.get('restart_policy')
            device.scheduler_name = spec.get('scheduler_name')
            device.service_account_name = spec.get('service_account_name')
            device.phase = status.get('phase')
            device.qos_class = status.get('qos_class')
            device.start_time = parse_date(status.get('start_time'))
            device.args = container.get('args')
            device.image = container.get('image')
            device.image_pull_policy = container.get('image_pull_policy')
            device.termination_message_path = container.get('termination_message_path')
            device.termination_message_policy = container.get('termination_message_policy')
            device.working_dir = container.get('working_dir')
            device.ready = parse_bool_from_raw(container.get('ready'))
            device.restart_count = int_or_none(container.get('restart_count'))

            for label_name, label_value in labels.items():
                try:
                    device.append_label(name=label_name, value=label_value)
                except Exception as err:
                    logger.debug(f'Failed to parse label: {str(err)}')

            for owner_reference in owner_references:
                try:
                    device.append_owner_references(
                        uid=owner_reference.get('uid'),
                        name=owner_reference.get('name'),
                        api_version=owner_reference.get('api_version'),
                        block_owner_deletion=parse_bool_from_raw(owner_reference.get('block_owner_deletion')),
                        controller=parse_bool_from_raw(owner_reference.get('controller')),
                        kind=owner_reference.get('kind')
                    )
                except Exception as err:
                    logger.debug(f'Failed to parse owner reference: {str(err)}')

            for volume_mount in volume_mounts:
                try:
                    device.append_volume_mount(
                        name=volume_mount.get('name'),
                        read_only=parse_bool_from_raw(volume_mount.get('read_only')),
                        path=volume_mount.get('mount_path'),
                        sub_path=volume_mount.get('sub_path')
                    )
                except Exception as err:
                    logger.debug(f'Failed to parse volume mount: {str(err)}')

            try:
                pod_ip = status.get('pod_ip')
                device.pod_ip = pod_ip

                # This could be removed after merging the new ip formatter.
                if isinstance(pod_ip, str):
                    pod_ip = [pod_ip]
                device.pod_ip_raw = pod_ip
            except Exception as e:
                logger.debug(f'Failed to parse pod ip: {str(e)}')

        except Exception as err:
            logger.exception(f'Failed creating instance for device {device_raw} ,  Error:{str(err)}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            container = get_value_or_default('container', device_raw.get('container'), dict)
            container_status = get_value_or_default('container_status', device_raw.get('container_status'), dict)

            primary_device_id = container_status.get('container_id')
            secondary_device_id = None

            pod_name = device_raw.get('name')
            name = container.get('name')
            image = container.get('image')

            if pod_name and image and name:
                secondary_device_id = f'{pod_name}_{image}_{name}'

            if not(primary_device_id or secondary_device_id):
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            device_id = f'{str(primary_device_id)}_{str(secondary_device_id)}'

            device.id = device_id
            device.name = name
            device.first_seen = parse_date(device_raw.get('creation_timestamp'))

            state = container_status.get('state')
            if (
                    state and
                    isinstance(state, dict) and
                    isinstance(state.get('running'), dict) and
                    isinstance(state.get('running').get('started_at'), str)
            ):
                device.last_seen = parse_date(state.get('running').get('started_at'))

            try:
                status = get_value_or_default('status', device_raw.get('status'), dict)
                device.add_ips_and_macs(ips=status.get('host_ip'))
            except Exception as e:
                logger.debug(f'Failed to parse host ip: {str(e)}')

            self._fill_kubernetes_device_fields(device_raw, device)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Kubernetes Device for {device_raw}')
            return None

    @staticmethod
    def _flattening_raw_devices(pods_raw_data):
        """
        :param pods_raw_data: raw data of pods
        :return: flat raw data of containers includes their pod's details
        """

        for pod_raw in pods_raw_data:
            spec = get_value_or_default('spec', pod_raw.get('spec'), dict)
            containers = get_value_or_default('containers', spec.pop('containers', []), list)
            status = get_value_or_default('status', pod_raw.get('status'), dict)
            container_statuses = get_value_or_default('container_status', status.pop('container_statuses', []), list)

            for container in containers:
                container = get_value_or_default('container', container, dict)
                flat_raw_device = pod_raw
                flat_raw_device.update(container)

                for container_status in container_statuses:
                    container_status = get_value_or_default('cotnainer_status', container_status, dict)
                    if not (container_status and container):
                        continue
                    if container_status.get('image') == container.get('image'):
                        flat_raw_device['container_status'] = container_status
                        break
                yield flat_raw_device

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """

        for device_raw in self._flattening_raw_devices(devices_raw_data):
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Kubernetes Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Virtualization]
