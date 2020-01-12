import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from netskope_adapter.connection import NetskopeConnection
from netskope_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')

STATUS_DICT = {0: 'Disabled', 1: 'Enabled', 2: 'Uninstalled'}
OS_DICT = {0: 'Windows', 1: 'Mac', 3: 'Android', 4: 'Windows Server'}
ACTOR_DICT = {0: 'User', 1: 'Admin', 2: 'System'}
EVENT_DICT = {0: 'Installed', 1: 'Tunnel Up', 2: 'Tunnel Down', 3: 'Tunnel down due to Secure Forwarder',
              4: 'Tunnel down due to config error', 5: 'Tunnel down due to error',
              6: 'User Disabled', 7: 'User Enabled', 8: 'Admin Disabled',
              9: 'Admin Enabled', 10: 'Uninstalled', 11: 'Installation Failure'}
CLASSIFICATION_DICT = {0: 'Managed', 1: 'Unmanaged', 2: 'Unknown'}


class NetskopeAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        last_status = Field(str, 'Last Status')
        last_event = Field(str, 'Last Event')
        lsat_actor = Field(str, 'Last Actor')
        device_classification_status = Field(str, 'Device Classification Status')

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
        connection = NetskopeConnection(domain=client_config['domain'],
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
        The schema NetskopeAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Netskope Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Token',
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
            device_id = device_raw.get('device_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + ((device_raw.get('host_info') or {}).get('hostname') or '')
            host_info_raw = device_raw.get('host_info') or {}
            device.hostname = host_info_raw.get('hostname')
            try:
                device.figure_os((OS_DICT.get(host_info_raw.get('os')) or '')
                                 + ' ' + (host_info_raw.get('os_version') or ''))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            device.device_model = host_info_raw.get('device_model')
            device.device_manufacturer = host_info_raw.get('device_make')
            device.first_seen = parse_date(device_raw.get('client_install_time'))
            try:
                last_event_raw = device_raw.get('last_event') or {}
                device.last_seen = parse_date(last_event_raw.get('timestamp'))
                device.last_status = STATUS_DICT.get(last_event_raw.get('status'))
                device.last_event = EVENT_DICT.get(last_event_raw.get('event'))
                device.lsat_actor = ACTOR_DICT.get(last_event_raw.get('actor'))
            except Exception:
                logger.exception(f'Probelm getting last event')
            users_raw = device_raw.get('users')
            if not isinstance(users_raw, list):
                users_raw = []
            for user_raw in users_raw:
                if isinstance(user_raw, dict) and user_raw.get('username'):
                    device.last_used_users.append(user_raw.get('username'))
            device.device_classification_status = CLASSIFICATION_DICT.get(
                device_raw.get('device_classification_status'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Netskope Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
