import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.parsing import figure_out_cloud
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_valid_ip
from axonius.utils.files import get_local_config_file
from alcide_adapter.connection import AlcideConnection
from alcide_adapter.client_id import get_client_id
from alcide_adapter.structures import AlcideDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class AlcideAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(AlcideDeviceInstance):
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
        connection = AlcideConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      org=client_config['org'],
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
        The schema AlcideAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Alcide Domain',
                    'type': 'string'
                },
                {
                    'name': 'org',
                    'title': 'Organization UID',
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
                'org',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements
    @staticmethod
    def _fill_alcide_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            kernel_version = None
            device.namespace = device_raw.get('namespace')
            device.monitor_time = parse_date(device_raw.get('monitorTime'))
            device.agent_time = parse_date(device_raw.get('agentTime'))
            device.monitor_active = device_raw.get('monitorActive') \
                if isinstance(device_raw.get('monitorActive'), bool) else None
            device.agent_active = device_raw.get('agentActive') \
                if isinstance(device_raw.get('agentActive'), bool) else None
            device.datacenter = device_raw.get('datacenter')
            device.cluster = device_raw.get('cluster')
            device.label = device_raw.get('label')
            device.meta_type = device_raw.get('metaType')
            uid = device_raw.get('uid')
            device.uid = uid
            if uid and uid.startswith('i-'):
                device.cloud_id = uid
            metadata_labels = device_raw.get('metadataLabels')
            os_str = ''
            if not isinstance(metadata_labels, list):
                metadata_labels = []
            for meta_raw in metadata_labels:
                if not isinstance(meta_raw, dict):
                    continue
                meta_key = meta_raw.get('key')
                meta_value = meta_raw.get('value')
                device.add_key_value_tag(key=meta_key, value=meta_value)
            metadata = device_raw.get('metadata')
            if not isinstance(metadata, list):
                metadata = []
            for meta_raw in metadata:
                if not isinstance(meta_raw, dict):
                    continue
                meta_key = meta_raw.get('key')
                meta_value = meta_raw.get('value')
                if meta_key == 'CREATION_TIME_STAMP':
                    device.first_seen = parse_date(meta_value)
                elif meta_key == 'ORCHESTRATOR_TYPE':
                    device.orchestrator_type = meta_value
                elif meta_key == 'NODE_AGENT_VERSION':
                    device.node_agent_version = meta_value
                elif meta_key == 'IMAGES':
                    device.images = meta_value
                elif meta_key == 'BOOT_ID':
                    device.boot_id = meta_value
                elif meta_key == 'VIRTUALIZATION_ENGINE':
                    device.virtualization_engine = meta_value
                elif meta_key == 'VIRTUALIZATION_VERSION':
                    device.virtualization_version = meta_value
                elif meta_key == 'ORCHESTRATION_AGENT_VERSION':
                    device.orchestration_agent_version = meta_value
                elif meta_key == 'CLOUD_PROVIDER_TYPE':
                    device.cloud_provider = figure_out_cloud(meta_value)
                elif meta_key in ['OPERATING_SYSTEM', 'OS_VERSION', 'ARCHITECTURE']:
                    os_str += ' ' + meta_value
                elif meta_key == 'KERNEL_VERSION':
                    kernel_version = meta_value
                elif meta_key == 'MEMORY':
                    try:
                        device.total_physical_memory = float(meta_value)
                    except Exception:
                        pass
                elif meta_key == 'CPU':
                    try:
                        device.total_number_of_cores = int(meta_value)
                    except Exception:
                        pass
            device.figure_os(os_str)
            try:
                device.os.kernel_version = kernel_version
            except Exception:
                pass
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('name')
            try:
                ip_addresses = device_raw.get('ipAddresses')
                if not isinstance(ip_addresses, list):
                    ip_addresses = []
                for ip_raw in ip_addresses:
                    ips = ip_raw.get('address')
                    if not ips:
                        continue
                    ips = [ip for ip in ips if is_valid_ip(ip)]
                    device.add_nic(ips=ips)
            except Exception:
                logger.exception(f'Problem with ips')

            self._fill_alcide_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching Alcide Device for {device_raw}')
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
                logger.exception(f'Problem with fetching Alcide Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
