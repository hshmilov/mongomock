import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from eclypsium_adapter.connection import EclypsiumConnection
from eclypsium_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class EclypsiumAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        last_scan_date = Field(datetime.datetime, 'Last Scan Date')
        online = Field(bool, 'Online')
        product = Field(str, 'Product')
        is_updated = Field(bool, 'Is Updated')
        device_type = Field(str, 'Device Type')
        auth_scheme = Field(str, 'Auth Scheme')
        update_url = Field(str, 'Update Url')
        active_threats = Field(int, 'Active Threats')

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
        connection = EclypsiumConnection(domain=client_config['domain'],
                                         verify_ssl=client_config['verify_ssl'],
                                         https_proxy=client_config.get('https_proxy'),
                                         client_id=client_config['client_id'],
                                         client_secret=client_config['client_secret'],
                                         )
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
        The schema EclypsiumAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Eclypsium Domain',
                    'type': 'string'
                },
                {
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
                    'title': 'Client Secret',
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
                'client_secret',
                'client_id',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('hostname') or '')
            device.hostname = device_raw.get('hostname')
            device.last_seen = parse_date(device_raw.get('lastSeen'))
            device.last_scan_date = parse_date(device_raw.get('lastScanDate'))
            device.online = device_raw.get('online')\
                if isinstance(device_raw.get('online'), bool) else None
            macs = device_raw.get('macAddresses')
            if not isinstance(macs, list):
                macs = []
            ips = []
            ips_raw = device_raw.get('ip')
            if not isinstance(ips_raw, list):
                ips_raw = []
            for ip_raw in ips_raw:
                if isinstance(ip_raw, dict) and ip_raw.get('ipString'):
                    ips.append(ip_raw.get('ipString'))
            if ips or macs:
                device.add_ips_and_macs(ips=ips, macs=macs)
            device.figure_os(device_raw.get('os'))
            device.product = device_raw.get('product')
            device.add_agent_version(agent=AGENT_NAMES.eclypsium,
                                     version=device_raw.get('collectedAgentVersion'))

            device.first_seen = parse_date(device_raw.get('createdAt'))
            device.auth_scheme = device_raw.get('authScheme')
            device.device_manufacturer = device_raw.get('manufacturer')
            device.device_model = device_raw.get('model')
            device.update_url = device_raw.get('updateUrl')
            device.device_type = device_raw.get('type')
            device.active_threats = device_raw.get('activeThreats') \
                if isinstance(device_raw.get('activeThreats'), int) else None
            device.is_updated = device_raw.get('isEndpointUpToDate')\
                if isinstance(device_raw.get('isEndpointUpToDate'), bool) else None
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Eclypsium Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
