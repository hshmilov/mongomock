import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from omnivista_adapter.connection import OmnivistaConnection
from omnivista_adapter.client_id import get_client_id
from omnivista_adapter.consts import MANAGED_DEVICE

logger = logging.getLogger(f'axonius.{__name__}')


class OmnivistaAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Device Type')
        seen_by = ListField(str, 'Seen By')
        traps = Field(str, 'Traps')
        location = Field(str, 'Location')
        last_upgrade_status = Field(str, 'Last Upgrade Status')
        device_version = Field(str, 'Device Version')
        device_status = Field(str, 'Device Status')
        running_from = Field(str, 'Running From')
        changes = ListField(str, 'Changes')

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
        connection = OmnivistaConnection(domain=client_config['domain'],
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
        The schema OmnivistaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Omnivista Domain',
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
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_managed_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('macAddress')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.name = device_raw.get('name')
            device.add_nic(mac=device_raw.get('macAddress'), ips=[device_raw.get('ipAddress')])
            device.device_type = device_raw.get('deviceType')
            if isinstance(device_raw.get('seenBy'), str) and device_raw.get('seenBy'):
                device.seen_by = [seen_by_raw.strip() for seen_by_raw in device_raw.get('seenBy').split(',')]
            if isinstance(device_raw.get('changes'), str) and device_raw.get('changes'):
                device.changes = [changes_raw.strip() for changes_raw in device_raw.get('changes').split(',')]
            device.traps = device_raw.get('traps')
            device.location = device_raw.get('location')
            device.first_seen = parse_date(device_raw.get('discoveredDateTime'))
            device.device_version = device_raw.get('version')
            device.last_seen = parse_date(device_raw.get('lastKnownUpAt'))
            device.description = device_raw.get('description')
            device.device_status = device_raw.get('status')
            device.running_from = device_raw.get('runningFrom')
            device.hostname = device_raw.get('deviceDNS')
            device.last_upgrade_status = device_raw.get('deviceLastUpgradeStatus')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Omnivista Device for {device_raw}')
            return None

    def _create_cirrus_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('') or '')
            # AUTOADAPTER - create device
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Omnivista Device for {device_raw}')
            return None

    def _create_ov_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('') or '')
            # AUTOADAPTER - create device
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Omnivista Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == MANAGED_DEVICE:
                device = self._create_managed_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
