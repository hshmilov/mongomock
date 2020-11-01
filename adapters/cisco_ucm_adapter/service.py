import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.cisco_ucm.connection import CiscoUcmConnection
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, parse_date
from cisco_ucm_adapter.client_id import get_client_id
from cisco_ucm_adapter.structures import CicsoUcmDeviceAdapter

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoUcmAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(CicsoUcmDeviceAdapter):
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
        connection = CiscoUcmConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        username=client_config['username'],
                                        password=client_config['password'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(fetch_inactive_devices=self.__fetch_inactive_devices)

    @staticmethod
    def _clients_schema():
        """
        The schema CiscoUcmAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cisco UCM Domain',
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

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()

            device_id = device_raw.get('uuid')
            if not device_id:
                logger.warning(f'Bad device with no id: {device_raw}')
                return None

            device.id = f'{device_id}_{device_raw.get("name") or ""}'
            device.description = device_raw.get('description')
            device.name = device_raw.get('name')
            device.uuid = device_raw.get('uuid')
            device.owner = device_raw.get('ownerUserName')
            device.device_model = device_raw.get('model')

            if parse_bool_from_raw(device_raw.get('isActive')) is not None:
                device.device_disabled = not parse_bool_from_raw(device_raw.get('isActive'))

            hostname = device_raw.get('name')
            if isinstance(hostname, str) and hostname.startswith('SEP'):
                # This would either take the form of `SEPMACADDRESS123` OR `SEPSOMEHOSTNAME`
                # In some cases the SEP tag won't be there
                # And in some cases it won't be a valid MAC at all
                # So try to find a mac in there, and if not log the error
                mac = hostname[3:]
            else:
                mac = hostname
            device.add_nic(mac=mac)
            device.last_seen = parse_date(device_raw.get('loginTime'))

            device.protocol = device_raw.get('protocol')
            device.protocol_side = device_raw.get('protocolSide')
            device.product = device_raw.get('product')
            device.class_id = device_raw.get('class')
            device.network_location = device_raw.get('networkLocation')
            device.dual_mode = parse_bool_from_raw(device_raw.get('isDualMode'))
            device.protected = parse_bool_from_raw(device_raw.get('isProtected'))

            device.set_raw(device_raw)
            return device

        except Exception:
            logger.exception(f'Problem with fetching CiscoUcm Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Manager, AdapterProperty.Network]

    @classmethod
    def _db_config_schema(cls) -> dict:
        """
        Return the schema this class wants to have for the config
        """
        return {
            'items': [
                {
                    'name': 'fetch_inactive_devices',
                    'title': 'Fetch inactive devices',
                    'type': 'bool'
                }
            ],
            'required': [
                'fetch_inactive_devices'
            ],
            'pretty_name': 'Cisco UCM Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        """
        Return the default configuration for this class
        """
        return {
            'fetch_inactive_devices': False
        }

    def _on_config_update(self, config):
        """
        Virtual
        This is called on every inheritor when the config was updated.
        """
        self.__fetch_inactive_devices = parse_bool_from_raw(config.get('fetch_inactive_devices')) or False
