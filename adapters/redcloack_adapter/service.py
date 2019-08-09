import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.fields import Field, ListField
from redcloack_adapter.connection import RedcloackConnection
from redcloack_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class RedcloackAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        color = Field(str, 'Color')
        red_tag = ListField(str, 'Redcloak Tag')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability('https://api.secureworks.com/')

    @staticmethod
    def get_connection(client_config):
        connection = RedcloackConnection(verify_ssl=client_config['verify_ssl'],
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
                'https://api.secureworks.com/', str(e))
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
        The schema RedcloackAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'username',
                    'title': 'API Zone User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'API Zone Password',
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('host_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('host_name') or '')
            device.name = device_raw.get('host_name')
            device.color = device_raw.get('color')
            try:
                device.red_tag = device_raw.get('tag')
            except Exception:
                logger.exception(f'Problem with tag at {device_raw}')
            try:
                device.last_seen = parse_date(device_raw.get('last_connect_time'))
            except Exception:
                logger.exception(f'Problem getting last seen for {device_raw}')
            try:
                system_info = device_raw.get('system_information')
                if system_info:
                    device.hostname = system_info.get('host_name')
                    device.bios_serial = system_info.get('bios_serial')
                    ips = system_info.get('ip_address')
                    device.add_ips_and_macs(None, ips)
                    device.add_agent_version(agent=AGENT_NAMES.redcloak, version=system_info.get('redcloak_version'))
                    if system_info.get('logon_user') and isinstance(system_info.get('logon_user'), list):
                        device.last_used_users = system_info.get('logon_user')
                    try:
                        device.figure_os(system_info.get('version'))
                    except Exception:
                        logger.exception(f'Problem getting os for {device_raw}')
            except Exception:
                logger.exception(f'Problem getting extra info for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Redcloack Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
