import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.netiq.connection import NetiqConnection
from axonius.clients.netiq.consts import LOGIN_METHODS_LIST
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from netiq_adapter.client_id import get_client_id
from netiq_adapter.structures import NetiqDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class NetiqAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(NetiqDeviceInstance):
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
        connection = NetiqConnection(domain=client_config.get('domain'),
                                     login_method=client_config.get('login_method'),
                                     verify_ssl=client_config.get('verify_ssl'),
                                     https_proxy=client_config.get('https_proxy'),
                                     proxy_username=client_config.get('proxy_username'),
                                     proxy_password=client_config.get('proxy_password'),
                                     username=client_config.get('username'),
                                     password=client_config.get('password'))
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
        The schema NetiqAdapter expects from configs

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
                    'name': 'login_method',
                    'title': 'Login Method',
                    'type': 'string',
                    'enum': LOGIN_METHODS_LIST,
                    'default': LOGIN_METHODS_LIST[0]
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
                'username',
                'password',
                'login_method',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_netiq_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.software_type = device_raw.get('software_type')
            device.device_type = int_or_none(device_raw.get('typ'))
            device.trusted = parse_bool_from_raw(device_raw.get('is_trusted'))
            device.local = parse_bool_from_raw(device_raw.get('is_local'))
            device.device_id = device_raw.get('device_id')
            device.software_version = device_raw.get('software_ver')
        except Exception:
            logger.exception(f'Failed creating instance for endpoints {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.name = device_raw.get('name')
            device.description = device_raw.get('desc')
            is_enabled = parse_bool_from_raw(device_raw.get('is_enabled'))
            if is_enabled is not None:
                device.device_disabled = not is_enabled

            device.owner = device_raw.get('owner')
            device.last_seen = parse_date(device_raw.get('last_session'))

            if isinstance(device_raw.get('os'), dict):
                os_raw = device_raw.get('os')
                os_string = f'{str(os_raw.get("display_name") or "")} {str(os_raw.get("platform") or "")} ' \
                            f'{str(device_raw.get("version") or "")} {str(device_raw.get("type") or "")}'
                device.figure_os(os_string=os_string)

            self._fill_netiq_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching NetIQ Endpoint for {device_raw}')
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
                logger.exception(f'Problem with fetching NetIQ Endpoint for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
