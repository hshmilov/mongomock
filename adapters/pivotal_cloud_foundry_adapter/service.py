import logging
import datetime
from urllib.parse import urlparse

from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.adapter_exceptions import ClientConnectionException
from pivotal_cloud_foundry_adapter.connection import PivotalCloudFoundryConnection
from pivotal_cloud_foundry_adapter.client_id import get_client_id
from pivotal_cloud_foundry_adapter.structures import PivotalCloudFoundryInstance
from pivotal_cloud_foundry_adapter.consts import URL_DEFAULT_API_PATH, URL_DEFAULT_UAA_PATH

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class PivotalCloudFoundryAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(PivotalCloudFoundryInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _create_urls(client_config):
        parsed_url = urlparse(client_config['domain'])
        domain = parsed_url.netloc or parsed_url.path
        scheme = parsed_url.scheme or 'https'

        api_url = URL_DEFAULT_API_PATH.format(scheme, domain)
        uaa_url = URL_DEFAULT_UAA_PATH.format(scheme, domain)

        return uaa_url, api_url

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        uaa_url, api_url = PivotalCloudFoundryAdapter._create_urls(client_config)

        return RESTConnection.test_reachability(api_url, https_proxy=client_config.get(
            'https_proxy')) and RESTConnection.test_reachability(uaa_url, https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        uaa_url, api_url = PivotalCloudFoundryAdapter._create_urls(client_config)

        connection = PivotalCloudFoundryConnection(domain=api_url,
                                                   uaa_domain=uaa_url,
                                                   verify_ssl=(client_config.get('verify_ssl') or False),
                                                   https_proxy=client_config.get('https_proxy'),
                                                   username=client_config['username'],
                                                   password=client_config['password'])
        with connection:
            pass  # check the connection credentials are valid
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
        The schema PivotalCloudFoundryAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User name',
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
    def _fill_pivotal_cloud_foundry_fields(device_raw, device_instance: MyDeviceAdapter):
        try:
            device_instance.container_age = device_raw.get('uptime')
            device_instance.state = device_raw.get('state')
            device_instance.type = device_raw.get('type')

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            if device_raw.get('guid') is None or device_raw.get('index') is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_raw.get('guid')) + '_' + str(device_raw.get('index'))

            device.name = device_raw.get('name')
            device.add_ips_and_macs(ips=[device_raw.get('host')])

            if device_raw.get('state') == 'RUNNING':
                device.last_seen = parse_date(datetime.datetime.utcnow())

            if device_raw.get('uptime'):
                device.set_boot_time(uptime=datetime.timedelta(seconds=device_raw.get('uptime')))

            # Convert bytes to GB
            if device_raw.get('mem_quota'):
                device.total_physical_memory = round(device_raw.get('mem_quota') / (1024 ** 3), 2)

            if isinstance(device_raw.get('usage'), dict) and \
                    device_raw.get('usage').get('mem') and device_raw.get('mem_quota'):
                device.free_physical_memory = round(device_raw.get('mem_quota') / (1024 ** 3), 2) - round(
                    device_raw.get('usage').get('mem') / (1024 ** 3), 2)

            self._fill_pivotal_cloud_foundry_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching PCF Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching PCF Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
