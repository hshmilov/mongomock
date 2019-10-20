import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from automox_adapter.connection import AutomoxConnection
from automox_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class AutomoxAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        org_id = Field(str, 'Organization Id')
        instance_id = Field(str, 'Instancef Id')
        last_refresh_time = Field(datetime.datetime, 'Last Refresh Time')
        last_update_time = Field(datetime.datetime, 'Last Update Time')
        automox_tags = ListField(str, 'Automox Tags')

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
        connection = AutomoxConnection(domain=client_config['domain'],
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
        The schema AutomoxAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Automox Domain',
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

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('name')
            if isinstance(device_raw.get('organization_id'), int):
                device.org_id = device_raw.get('organization_id')
            if isinstance(device_raw.get('ip_addrs'), list):
                device.add_nic(ips=device_raw.get('ip_addrs'))
            device.instance_id = device_raw.get('instance_id')
            device.last_refresh_time = parse_date(device_raw.get('last_refresh_time'))
            device.last_update_time = parse_date(device_raw.get('last_update_time'))
            device.figure_os((device_raw.get('os_family') or '') + ' ' + (device_raw.get('os_name') or ''))
            if isinstance(device_raw.get('tags'), list):
                device.automox_tags = device_raw.get('tags')
            device_details = device_raw.get('detail')
            if not isinstance(device_details, dict):
                device_details = {}
            nics = device_details.get('NICS')
            if not isinstance(nics, list):
                nics = []
            for nic in nics:
                try:
                    mac = nic.get('MAC') if nic.get('MAC') else None
                    ips = nic.get('IPS') if isinstance(nic.get('IPS'), list) else None
                    if mac or ips:
                        device.add_nic(mac=mac, ips=ips)
                except Exception:
                    logger.exception(f'Problem with nic {nic}')
            device.device_serial = device_details.get('SERIAL')
            device.device_model = device_details.get('MODEL')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Automox Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
