import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.parsing import parse_unix_timestamp
from rumble_adapter.connection import RumbleConnection
from rumble_adapter.client_id import get_client_id
from rumble_adapter.consts import DEFAULT_RUMBLE_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class RumbleAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        org_id = Field(str, 'Organization Id')
        site_id = Field(str, 'Site Id')
        created_at = Field(datetime.datetime, 'Created At')
        updated_at = Field(datetime.datetime, 'Updated At')
        device_type = Field(str, 'Device Type')
        alive = Field(bool, 'Alive')
        detected_by = Field(str, 'Detected By')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain') or DEFAULT_RUMBLE_DOMAIN)

    @staticmethod
    def get_connection(client_config):
        connection = RumbleConnection(domain=client_config.get('domain') or DEFAULT_RUMBLE_DOMAIN,
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
                                      apikey=client_config['apikey'],
                                      org_id=client_config['org_id'])
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
        The schema RumbleAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Rumble Network Discovery Domain',
                    'type': 'string',
                    'default': DEFAULT_RUMBLE_DOMAIN
                },
                {
                    'name': 'org_id',
                    'title': 'Organization Id',
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

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + str((device_raw.get('names') or ''))
            if device_raw.get('names') and isinstance(device_raw.get('names'), list):
                device.hostname = device_raw.get('names')[0]
            device.add_ips_and_macs(ips=device_raw.get('addresses'), macs=device_raw.get('macs'))
            device.last_seen = parse_unix_timestamp(device_raw.get('last_seen'))
            device.first_seen = parse_unix_timestamp(device_raw.get('first_seen'))
            device.alive = bool(device_raw.get('alive'))
            device.site_id = device_raw.get('site_id')
            device.created_at = parse_unix_timestamp(device_raw.get('created_at'))
            device.updated_at = parse_unix_timestamp(device_raw.get('updated_at'))
            device.org_id = device_raw.get('organization_id')
            device.detected_by = device_raw.get('detected_by')
            try:
                device.figure_os((device_raw.get('os') or '') + ' ' + (device_raw.get('os_version') or ''))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            device.set_raw({})
            return device
        except Exception:
            logger.exception(f'Problem with fetching Rumble Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
