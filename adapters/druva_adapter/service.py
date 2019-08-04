import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from druva_adapter.connection import DruvaConnection
from druva_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class DruvaAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        device_status = Field(str, 'Device Status')
        agent_version = Field(str, 'Agent Version')
        upgrade_state = Field(str, 'Upgrade State')
        total_backup_data = Field(str, 'Total Backup Data')
        added_on = Field(datetime.datetime, 'Added On')
        last_upgraded_on = Field(datetime.datetime, 'Last Upgraded On')

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
        connection = DruvaConnection(domain=client_config['domain'],
                                     verify_ssl=client_config['verify_ssl'],
                                     https_proxy=client_config.get('https_proxy'),
                                     username=client_config['client_id'],
                                     password=client_config['client_secret'])
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
        The schema DruvaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Druva Domain',
                    'type': 'string'
                },
                {
                    'name': 'client_id',
                    'title': 'Client Id',
                    'type': 'string'
                },
                {
                    'name': 'Client_secret',
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
                'client_id',
                'client_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw, users_data_dict):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('deviceID')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('deviceName') or '')
            device.hostname = device_raw.get('deviceName')
            device.device_serial = device_raw.get('serialNumber')
            device.figure_os((device_raw.get('platformOS') or '')
                             + ' ' + (device_raw.get('deviceOS') or '')
                             + ' ' + (device_raw.get('deviceOSVersion') or ''))
            device.uuid = device_raw.get('uuid')
            device.device_status = device_raw.get('deviceStatus')
            device.upgrade_state = device_raw.get('upgradeState')
            device.total_backup_data = device_raw.get('totalBackupData')
            device.added_on = parse_date(device_raw.get('addedOn'))
            device.first_seen = parse_date(device_raw.get('addedOn'))
            device.last_upgraded_on = parse_date(device_raw.get('lastUpgradedOn'))
            device.last_seen = parse_date(device_raw.get('lastConnected'))
            device.agent_version = device_raw.get('clientVersion')
            try:
                if device_raw.get('userID') and users_data_dict.get(device_raw.get('userID')):
                    user_raw = users_data_dict.get(device_raw.get('userID'))
                    if user_raw.get('userName'):
                        device.last_used_users = [user_raw.get('userName')]
            except Exception:
                logger.exception(f'Problem with user data for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Druva Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, users_data_dict in devices_raw_data:
            device = self._create_device(device_raw, users_data_dict)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
