import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from cisco_umbrella_adapter.connection import CiscoUmbrellaConnection
from cisco_umbrella_adapter.client_id import get_client_id
from cisco_umbrella_adapter.consts import DEFAULT_UMBRELLA_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoUmbrellaAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        agent_type = Field(str, 'Agent Type')
        agent_status = Field(str, 'Agent Status')
        ip_blocking = Field(bool, 'IP Blocking')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            if not client_config.get('domain'):
                domain = DEFAULT_UMBRELLA_DOMAIN
            else:
                try:
                    int(client_config['domain'])
                    domain = DEFAULT_UMBRELLA_DOMAIN
                except Exception:
                    domain = client_config['domain']
            connection = CiscoUmbrellaConnection(domain=domain,
                                                 verify_ssl=client_config.get('verify_ssl') or False,
                                                 network_api_key=client_config.get('network_api_key'),
                                                 network_api_secret=client_config.get('network_api_secret'),
                                                 management_api_key=client_config.get('management_api_key'),
                                                 management_api_secret=client_config.get('management_api_secret'),
                                                 https_proxy=client_config.get('https_proxy'),
                                                 msp_id=client_config.get('msp_id'))
            with connection:
                pass
            return connection
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
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema CiscoUmbrellaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CiscoUmbrella Domain',
                    'type': 'string',
                    'default': DEFAULT_UMBRELLA_DOMAIN
                },
                {
                    'name': 'network_api_key',
                    'title': 'Network API Key',
                    'type': 'string'
                },
                {
                    'name': 'network_api_secret',
                    'title': 'Network API Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'management_api_key',
                    'title': 'Management API Key',
                    'type': 'string'
                },
                {
                    'name': 'management_api_secret',
                    'title': 'Management API Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'msp_id',
                    'title': 'mspID',
                    'type': 'string',
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
                'network_api_key',
                'network_api_secret',
                'management_api_key',
                'management_api_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('deviceId')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = device_id + '_' + (device_raw.get('name') or '')
                device.hostname = device_raw.get('name')
                device.ip_blocking = device_raw.get('hasIpBlocking')
                try:
                    device.figure_os(device_raw.get('osVersionName'))
                except Exception:
                    logger.exception(f'Problem getting OS for {device_raw}')
                try:
                    device.last_seen = parse_date(device_raw.get('lastSync'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                device.agent_status = device_raw.get('status')
                device.agent_type = device_raw.get('type')
                device.agent_version = device_raw.get('version')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching CiscoUmbrella Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
