import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.cisco_security_manager.connection import CiscoSecurityManagerConnection
from axonius.clients.cisco_security_manager.consts import DEFAULT_ASYNC_CHUNKS
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from cisco_security_manager_adapter.client_id import get_client_id
from cisco_security_manager_adapter.structures import CiscoSecurityManagerDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class CiscoSecurityManagerAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(CiscoSecurityManagerDeviceInstance):
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
        connection = CiscoSecurityManagerConnection(domain=client_config.get('domain'),
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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(
                async_chunks=self.__async_chunks
            )

    @staticmethod
    def _clients_schema():
        """
        The schema CiscoSecurityManagerAdapter expects from configs

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
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_cisco_security_manager_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.image_name = device_raw.get('imageName')
            device.device_type = device_raw.get('deviceCapability')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('gid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.name = device_raw.get('name')
            device.hostname = device_raw.get('name')
            device.last_seen = parse_date(device_raw.get('lastUpdateTime'))
            device.add_public_ip(ip=device_raw.get('ipv4Address'))

            os_string = f'{device_raw.get("osType") or ""} {device_raw.get("osVersion") or ""}'
            device.figure_os(os_string=os_string)

            if isinstance(device_raw.get('mgmtInterface'), dict):
                managment_raw = device_raw.get('mgmtInterface')
                ips = None
                if isinstance(managment_raw.get('ipInterface'), dict):
                    ips = managment_raw.get('ipInterface').get('ipAddress') or []
                if isinstance(ips, str):
                    ips = [ips]
                device.add_nic(ips=ips,
                               name=managment_raw.get('type'))

            if isinstance(device_raw.get('interfaceList'), dict) and \
                    isinstance(device_raw.get('interfaceList').get('interface'), list):
                for interface_raw in device_raw.get('interfaceList').get('interface'):
                    if not isinstance(interface_raw, dict):
                        continue
                    try:
                        ips = None
                        if isinstance(interface_raw.get('ipInterface'), dict):
                            ips = interface_raw.get('ipInterface').get('ipAddress') or []

                        if isinstance(ips, str):
                            ips = [ips]
                        device.add_nic(ips=ips,
                                       name=interface_raw.get('type'))
                    except Exception:
                        pass

            self._fill_cisco_security_manager_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CiscoSecurityManager Device for {device_raw}')
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
                logger.exception(f'Problem with fetching CiscoSecurityManager Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'async_chunks',
                    'type': 'integer',
                    'title': 'Async chunks in parallel'
                }
            ],
            'required': [
                'async_chunks',
            ],
            'pretty_name': 'Cisco Security Manager Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'async_chunks': DEFAULT_ASYNC_CHUNKS
        }

    def _on_config_update(self, config):
        self.__async_chunks = config.get('async_chunks') or DEFAULT_ASYNC_CHUNKS
