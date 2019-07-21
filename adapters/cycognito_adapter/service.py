import logging

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from cycognito_adapter.connection import CycognitoConnection
from cycognito_adapter.client_id import get_client_id
from cycognito_adapter.consts import DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class PortInformation(SmartJsonClass):
    port_number = Field(int, 'Port Number')
    port_protocol = Field(str, 'Port Protocol')


class CycognitoAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        at_risk = Field(bool, 'At Risk')
        severe_issues_count = Field(int, 'Severe Issues Count')
        domain_names = ListField(str, 'Domain Names')
        locations = ListField(str, 'Locations')
        alive = Field(bool, 'Alive')
        security_rating = Field(str, 'Security Rating')
        owned_by = Field(str, 'Owned By')
        scan_status = Field(str, 'Scan Status')

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
        connection = CycognitoConnection(domain=client_config['domain'],
                                         verify_ssl=client_config['verify_ssl'],
                                         https_proxy=client_config.get('https_proxy'),
                                         realm=client_config['realm'],
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
        The schema CycognitoAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CyCognito Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN
                },
                {
                    'name': 'realm',
                    'title': 'User Realm',
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
                'realm',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('asset-id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id)
            ips = device_raw.get('ip')
            if isinstance(ips, str):
                ips = [ips]
            device.add_nic(ips=ips)
            if isinstance(device_raw.get('severe-issues-count'), int):
                device.severe_issues_count = device_raw.get('severe-issues-count')
            if isinstance(device_raw.get('domain-names'), list):
                device.domain_names = [str(dn) for dn in (device_raw.get('domain-names') or []) if dn]
            if isinstance(device_raw.get('locations'), list):
                device.locations = [str(location) for location in (device_raw.get('locations') or []) if location]
            device.alive = bool(device_raw.get('alive'))
            try:
                device.security_rating = device_raw.get('security-rating')
            except Exception:
                logger.exception(f'Problem adding security rating')
            open_ports_raw = device_raw.get('open-ports')
            if isinstance(open_ports_raw, list) and open_ports_raw:
                for open_port_raw in open_ports_raw:
                    try:
                        device.add_open_port(protocol=open_port_raw.get('protocol'),
                                             port_id=open_port_raw.get('port'))
                    except Exception:
                        logger.exception(f'Problem adding device open port {open_port_raw}')
            device.at_risk = bool(device_raw.get('at-risk'))
            device.owned_by = device_raw.get('owned-by')
            device.scan_status = device_raw.get('scan-status')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Cycognito Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
