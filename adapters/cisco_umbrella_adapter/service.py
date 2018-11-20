import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from cisco_umbrella_adapter.connection import CiscoUmbrellaConnection
from cisco_umbrella_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoUmbrellaAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        # AUTOADAPTER - add here device fields if needed
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with CiscoUmbrellaConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                         username=client_config['api_key'], password=client_config['api_secret'],
                                         https_proxy=client_config.get('https_proxy')) as connection:
                return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
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
        The schema CiscoUmbrellaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CiscoUmbrella Domain',
                    'type': 'string'
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

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                # AUTOADAPTER - create device
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching CiscoUmbrella Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
