import ipaddress
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from axonius.devices.device_adapter import AGENT_NAMES
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid
from infinipoint_adapter.connection import InfinipointConnection
from infinipoint_adapter.client_id import get_client_id
from infinipoint_adapter.structures import InfinipointDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class InfinipointAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(InfinipointDeviceInstance):
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
        connection = InfinipointConnection(domain=client_config['domain'],
                                           verify_ssl=client_config['verify_ssl'],
                                           https_proxy=client_config.get('https_proxy'),
                                           api_key=client_config['api_key'],
                                           api_secret=client_config['api_secret']
                                           )
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
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema InfinipointAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
                    'type': 'string',
                    'default': 'https://console.infinipoint.io'
                },
                {
                    'name': 'api_key',
                    'title': 'API Key',
                    'type': 'string'
                },
                {
                    'name': 'api_secret',
                    'title': 'API Secret',
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
                'api_key',
                'api_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_infinipoint_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            edge = device_raw.get('edge')
            if isinstance(edge, bool):
                device.edge = edge
            device.product_type = device_raw.get('productType')
            device_tags = device_raw.get('tags')
            if isinstance(device_tags, list):
                device.device_tags = device_tags
            device.policy_version = device_raw.get('policyVersion')
            device.client_type = device_raw.get('clientType')

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('host') or '')
            device.hostname = device_raw.get('host')
            device.last_seen = parse_date(device_raw.get('lastSeen'))
            device.first_seen = parse_date(device_raw.get('regDate'))
            mac = device_raw.get('macAddress')
            try:
                ip = device_raw.get('ip')
                ip = str(ipaddress.ip_address(ip))
            except Exception:
                ip = None
            device.add_ips_and_macs(ips=ip, macs=mac)
            device.figure_os(device_raw.get('osName'))
            device.add_agent_version(version=device_raw.get('agentVersion'),
                                     status=device_raw.get('status'),
                                     agent=AGENT_NAMES.infinipoint)
            if is_domain_valid(device_raw.get('domain')):
                device.domain = device_raw.get('domain')
            self._fill_infinipoint_device_fields(device_raw, device)
            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching Infinipoint Device for {device_raw}')
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
                logger.exception(f'Problem with fetching Infinipoint Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
