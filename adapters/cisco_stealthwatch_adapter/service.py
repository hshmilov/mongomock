import logging

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.files import get_local_config_file
from cisco_stealthwatch_adapter.client_id import get_client_id
from cisco_stealthwatch_adapter.connection import CiscoStealthwatchConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoStealthwatchAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        swaID = Field(int,
                      'Flow Collector ID',
                      description='The device ID of the Flow Collector associated with the exporter')
        fcName = Field(str, 'Flow Collector Name')
        exp_type = Field(str, 'Exporter Device Type', description='Exporter type as reported by API')
        reported_name = Field(str, 'Name reported')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config['smc_host'])

    @staticmethod
    def get_connection(client_config):
        connection = CiscoStealthwatchConnection(domain=client_config['smc_host'],
                                                 tenant=client_config['tenant_id'],
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
                client_config['smc_host'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint: disable=arguments-differ
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

    # pylint: disable=arguments-differ, C0301
    @staticmethod
    def _clients_schema():
        """
        The schema CiscoStealthwatchAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'smc_host',
                    'title': 'Cisco SMC Hostname',
                    'type': 'string'
                },
                {
                    'name': 'tenant_id',
                    'title': 'Tenant identifier',
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
                'smc_host',
                'tenant_id'
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('ipAddress')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + str(device_raw.get('swaId', ''))
            device.add_ips_and_macs(ips=[device_raw.get('ipAddress')])
            name = device_raw.get('name')
            if name != device_raw.get('ipAddress'):
                device.hostname = name
            else:
                logger.error(f'Did not get hostname for exporter device: {name}.')
            device.reported_name = device_raw.get('name')
            device.exp_type = device_raw.get('type')
            device.fcName = device_raw.get('flowCollectorName')
            try:
                device.swaID = int(device_raw.get('swaId')) if device_raw.get('swaId') else None
            except Exception:
                logger.exception(f'Could not parse swaId: {device_raw.get("swaId")}')
            device.set_raw(device_raw)
            return device
        except Exception as e:
            logger.exception(f'Problem with fetching Cisco Stealthwatch Exporter for {device_raw}: {str(e)}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Assets]
