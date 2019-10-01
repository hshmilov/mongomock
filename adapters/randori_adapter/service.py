import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from randori_adapter.connection import RandoriConnection
from randori_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class RandoriAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        confidence = Field(int, 'Confidence')
        max_confidence = Field(int, 'Max Confidence')
        ip_count = Field(int, 'IP Count')

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
        connection = RandoriConnection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
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
        The schema RandoriAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Randori Domain',
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
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-nested-blocks
    def _create_device(self, device_raw, hostname_to_ip_dict, ips_data_dict, port_info_dict):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('hostname') or '')
            device.hostname = device_raw.get('hostname')
            device.confidence = device_raw.get('confidence') if isinstance(device_raw.get('confidence'), int) else None
            device.first_seen = parse_date(device_raw.get('first_seen'))
            device.last_seen = parse_date(device_raw.get('last_seen'))
            device.max_confidence = device_raw.get('max_confidence')\
                if isinstance(device_raw.get('max_confidence'), int) else None
            device.ip_count = device_raw.get('ip_count') if isinstance(device_raw.get('ip_count'), int) else None
            try:
                ip_ids = hostname_to_ip_dict.get(device_id)
                if not isinstance(ip_ids, list):
                    ip_ids = []
                for ip_id in ip_ids:
                    try:
                        ip_data = ips_data_dict.get(ip_id)
                        ports_data = port_info_dict.get(ip_id)
                        if not isinstance(ports_data, list):
                            ports_data = []
                        if ip_data.get('ip_str'):
                            device.add_nic(ips=[ip_data.get('ip_str')])
                        for port_raw in ports_data:
                            try:
                                if port_raw.get('seen_open'):
                                    device.add_open_port(port_id=port_raw.get('port'))
                            except Exception:
                                logger.exception(f'Problem adding port {port_raw}')
                    except Exception:
                        logger.exception(f'Problem with ip_id {ip_id}')
            except Exception:
                logger.exception(f'Problem getting ip info for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Randori Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, hostname_to_ip_dict, ips_data_dict, port_info_dict in devices_raw_data:
            device = self._create_device(device_raw, hostname_to_ip_dict, ips_data_dict, port_info_dict)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
