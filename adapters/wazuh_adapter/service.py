import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from wazuh_adapter.connection import WazuhConnection
from wazuh_adapter.client_id import get_client_id
from wazuh_adapter.consts import DEFAULT_WAZUH_PORT

logger = logging.getLogger(f'axonius.{__name__}')


class WazuhAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        group = Field(str, 'Group')
        config_sum = Field(str, 'Config Sum')
        merged_sum = Field(str, 'Merged Sum')
        node_name = Field(str, 'Node Name')
        key = Field(str, 'Key')
        manager_host = Field(str, 'Manager Host')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'), port=client_config.get('port'))

    @staticmethod
    def get_connection(client_config):
        connection = WazuhConnection(domain=client_config['domain'],
                                     port=client_config.get('port') or DEFAULT_WAZUH_PORT,
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
        The schema WazuhAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Wazuh Domain',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'default': DEFAULT_WAZUH_PORT,
                    'type': 'integer',
                    'format': 'port'
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
                'port',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('name')
            device.group = device_raw.get('group')
            device.config_sum = device_raw.get('configSum')
            device.merged_sum = device_raw.get('mergedSum')
            if device_raw.get('ip'):
                device.add_nic(ips=[device_raw.get('ip')])
            device.node_name = device_raw.get('node_name')
            device.first_seen = parse_date(device_raw.get('dateAdd'))
            device.add_agent_version(agent=AGENT_NAMES.wazuh,
                                     status=device_raw.get('status'),
                                     version=device_raw.get('version'))
            device.key = device_raw.get('key')
            device.manager_host = device_raw.get('manager_host')
            device.last_seen = parse_date(device_raw.get('lastKeepAlive'))
            os_raw = device_raw.get('os')
            if not isinstance(os_raw, dict):
                os_raw = {}
            device.figure_os((os_raw.get('platform') or '') + ' ' +
                             (os_raw.get('name') or '') + ' ' + (os_raw.get('version') or ''))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Wazuh Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
