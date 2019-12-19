import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.parsing import is_domain_valid
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from paloalto_xdr_adapter.connection import PaloaltoXdrConnection
from paloalto_xdr_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class PaloaltoXdrAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        endpoint_type = Field(str, 'Endpoint Type')
        group_name = Field(str, 'Group Name')
        install_date = Field(datetime.datetime, 'Install Date')
        installation_package = Field(str, 'Installation Package')
        content_version = Field(str, 'Content Version')
        alias = Field(str, 'Alias')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = PaloaltoXdrConnection(domain=client_config['domain'],
                                           verify_ssl=client_config['verify_ssl'],
                                           https_proxy=client_config.get('https_proxy'),
                                           api_key_id=client_config['api_key_id'],
                                           apikey=client_config['apikey'])
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
        The schema PaloaltoXdrAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'PaloaltoXdr Domain',
                    'type': 'string'
                },
                {
                    'name': 'api_key_id',
                    'title': 'API Key ID',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
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
                'api_key_id',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('endpoint_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('endpoint_name') or '')
            device.hostname = device_raw.get('endpoint_name')
            device.figure_os(device_raw.get('os_type'))
            if device_raw.get('users') and isinstance(device_raw.get('users'), list):
                device.last_used_users = device_raw.get('users')

            device.add_agent_version(agent=AGENT_NAMES.traps,
                                     version=device_raw.get('endpoint_version'),
                                     status=device_raw.get('endpoint_status'))
            device.endpoint_type = device_raw.get('endpoint_type')
            domain = device_raw.get('domain')
            if is_domain_valid(domain):
                device.domain = domain
            device.is_isolated = device_raw.get('is_isolated') \
                if isinstance(device_raw.get('is_isolated'), bool) else None
            device.group_name = device_raw.get('group_name')
            device.install_date = parse_date(device_raw.get('install_date'))
            device.installation_package = device_raw.get('installation_package')
            device.content_version = device_raw.get('content_version')
            device.last_seen = parse_date(device_raw.get('last_seen'))
            device.first_seen = parse_date(device_raw.get('first_seen'))
            if isinstance(device_raw.get('ip'), str) and device_raw.get('ip'):
                device.add_nic(ips=device_raw.get('ip').split(','))
            device.alias = device_raw.get('alias')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching PaloaltoXdr Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
