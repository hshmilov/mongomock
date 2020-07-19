import logging

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.parsing import is_valid_ip
from axonius.utils.files import get_local_config_file
from bigid_adapter.connection import BigidConnection
from bigid_adapter.client_id import get_client_id
from bigid_adapter.structures import BigidDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class BigidAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(BigidDeviceInstance):
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
        connection = BigidConnection(domain=client_config['domain'],
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
        The schema BigidAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'BigID Domain',
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
    def _create_device(hostname: str, device: MyDeviceAdapter, catalogs_data):
        try:
            device.id = hostname
            if not is_valid_ip(hostname):
                device.hostname = hostname
            else:
                device.add_nic(ips=[hostname])
            device.catalogs_data = catalogs_data
            device.set_raw({})

            return device
        except Exception:
            logger.exception(f'Problem with fetching Bigid Device for {hostname}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for hostname, catalogs_data in devices_raw_data:
            try:
                # noinspection PyTypeChecker
                device = self._create_device(hostname, self._new_device_adapter(), catalogs_data)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Bigid Device for {hostname}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
