import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.ivanti_endpoint_security.connection import IvantiEndpointSecurityConnection
from axonius.clients.ivanti_endpoint_security.consts import DEFAULT_API_PORT
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw
from ivanti_endpoint_security_adapter.client_id import get_client_id
from ivanti_endpoint_security_adapter.structures import IvantiEndpointSecurityDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class IvantiEndpointSecurityAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(IvantiEndpointSecurityDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                port=client_config.get('port'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = IvantiEndpointSecurityConnection(domain=client_config['domain'],
                                                      port=client_config.get('port'),
                                                      verify_ssl=client_config['verify_ssl'],
                                                      https_proxy=client_config.get('https_proxy'),
                                                      proxy_username=client_config.get('proxy_username'),
                                                      proxy_password=client_config.get('proxy_password'),
                                                      token=client_config['token'])
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
    def _clients_schema():
        """
        The schema IvantiEndpointSecurityAdapter expects from configs

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
                    'default': DEFAULT_API_PORT,
                    'format': 'port'
                },
                {
                    'name': 'token',
                    'title': 'API Token',
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
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
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

    @staticmethod
    def _fill_ivanti_endpoint_security_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.status = device_raw.get('Status')
            device.manifest_version = device_raw.get('Version')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('Id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('Name') or '')

            device.name = device_raw.get('Name')
            device.hostname = device_raw.get('Name')
            device.uuid = device_raw.get('Guid')
            device_enabled = parse_bool_from_raw(device_raw.get('Enabled'))
            if isinstance(device_enabled, bool):
                device.device_disabled = not device_enabled
            device.first_seen = parse_date(device_raw.get('InstallDate'))
            device.last_seen = parse_date(device_raw.get('LastContactDate'))

            ips = device_raw.get('IpAddress') or []
            if isinstance(ips, str):
                ips = [ips]
            device.add_nic(mac=device_raw.get('MacAddress'),
                           ips=ips)

            self._fill_ivanti_endpoint_security_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching IvantiEndpointSecurity Device for {device_raw}')
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
                logger.exception(f'Problem with fetching IvantiEndpointSecurity Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Endpoint_Protection_Platform]
