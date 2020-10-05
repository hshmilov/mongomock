import logging

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.intrigue.connection import IntrigueConnection
from axonius.clients.intrigue.consts import DEFAULT_DOMAIN
from axonius.utils.datetime import parse_date
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw
from intrigue_adapter.client_id import get_client_id
from intrigue_adapter.structures import IntrigueDeviceInstance, ResolutionData

logger = logging.getLogger(f'axonius.{__name__}')


class IntrigueAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(IntrigueDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(DEFAULT_DOMAIN,
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = IntrigueConnection(domain=DEFAULT_DOMAIN,
                                        verify_ssl=client_config.get('verify_ssl'),
                                        https_proxy=client_config.get('https_proxy'),
                                        proxy_username=client_config.get('proxy_username'),
                                        proxy_password=client_config.get('proxy_password'),
                                        access_key=client_config.get('access_key'),
                                        secret_key=client_config.get('secret_key'),
                                        collection_name=client_config.get('collection_name')
                                        )
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                DEFAULT_DOMAIN, str(e))
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
        The schema IntrigueAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'collection_name',
                    'type': 'string',
                    'title': 'Collection Name'
                },
                {
                    'name': 'access_key',
                    'title': 'Access API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'secret_key',
                    'title': 'Secret API Key',
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
                'collection_name',
                'access_key',
                'secret_key',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_intrigue_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.net_name = device_raw.get('net_name')
            resolutions = device_raw.get('resolutions')
            if not isinstance(resolutions, list):
                resolutions = []
            for resolution in resolutions:
                try:
                    response_type = resolution.get('response_type')
                    response_data = resolution.get('response_data')
                    device.resolutions.append(ResolutionData(response_type=response_type,
                                                             response_data=response_data))
                except Exception:
                    logger.exception(f'Problem with resolution')
            device.scoped = parse_bool_from_raw(device_raw.get('scoped'))
            device.hidden = parse_bool_from_raw(device_raw.get('hidden'))
            geolocation = device_raw.get('geolocation')
            if not isinstance(geolocation, dict):
                geolocation = dict()
            device.continent = geolocation.get('continent')
            device.country = geolocation.get('country')
            device.city = geolocation.get('city')
            device.subdivisions = geolocation.get('subdivisions') \
                if isinstance(geolocation.get('subdivisions'), list) else None
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('ip')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id)
            device.add_nic(ips=[device_id])
            device.first_seen = parse_date(device_raw.get('first_seen'))
            device.last_seen = parse_date(device_raw.get('last_seen'))
            device.figure_os(device_raw.get('os'))
            ports = device_raw.get('ports')
            if not isinstance(ports, list):
                ports = []
            for port in ports:
                try:
                    protocol = port.get('protocol')
                    number = port.get('number')
                    if number[-2] == 'e':
                        number = number[:-2]
                    if number.startswith('0.'):
                        number = number[2:]
                    number = int(number)
                    device.add_open_port(port_id=number, protocol=protocol)
                except Exception:
                    logger.exception(f'Problem with Port')
            self._fill_intrigue_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Intrigue Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for ip, device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                device_raw['ip'] = ip
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Intrigue Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
