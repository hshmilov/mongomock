import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from maas360_adapter.connection import Maas360Connection
from maas360_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class Maas360Adapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        ownership = Field(str, 'Ownership')
        installed_date = Field(datetime.datetime, 'Installed Date')
        custom_asset_number = Field(str, 'Custom Asset Number')
        device_owner = Field(str, 'Device Owner')
        email = Field(str, 'Email Address')
        mdm_device_type = Field(str, 'Maas360 Device Type')
        device_status = Field(str, 'Device Status')
        maas_status = Field(str, 'Maas360 Managed Status')
        udid = Field(str, 'Udid')
        mailbox_managed = Field(str, 'Mailbox Managed')

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
        connection = Maas360Connection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       username=client_config['username'],
                                       password=client_config['password'],
                                       billing_id=client_config['billing_id'],
                                       app_id=client_config['app_id'],
                                       app_version=client_config['app_version'],
                                       platform_id=client_config['platform_id'],
                                       app_access_key=client_config['app_access_key'])
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
        The schema Maas360Adapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'IBM MaaS360 Domain',
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
                    'name': 'billing_id',
                    'title': 'Billing Id',
                    'type': 'string'
                },
                {
                    'name': 'app_id',
                    'title': 'Application Id',
                    'type': 'string'
                },
                {
                    'name': 'app_version',
                    'title': 'Application Version',
                    'type': 'string'
                },
                {
                    'name': 'platform_id',
                    'title': 'Platform Id',
                    'type': 'string'
                },
                {
                    'name': 'app_access_key',
                    'title': 'Application Access Key',
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
                'verify_ssl',
                'billing_id',
                'app_access_key',
                'platform_id',
                'app_version',
                'app_id'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('maas360DeviceID')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('deviceName') or '')
            device.name = device_raw.get('deviceName')
            device.ownership = device_raw.get('ownership')
            device.custom_asset_number = device_raw.get('customAssetNumber')
            device.device_owner = device_raw.get('deviceOwner')
            if device_raw.get('username') and isinstance(device_raw.get('username'), str):
                device.last_used_users = device_raw.get('username').split(',')
            device.email = device_raw.get('emailAddress')
            device.mdm_device_type = device_raw.get('deviceType')
            device.device_manufacturer = device_raw.get('manufacturer')
            device.device_model = device_raw.get('model')
            device.figure_os(device_raw.get('osName'))
            device.imei = device_raw.get('imeiEsn')
            device.installed_date = parse_date(device_raw.get('installedDate'))
            device.last_seen = parse_date(device_raw.get('lastReported'))
            device.device_status = device_raw.get('deviceStatus')
            device.maas_status = device_raw.get('maas360ManagedStatus')
            device.udid = device_raw.get('udid')
            device.add_nic(mac=device_raw.get('wifiMacAddress'))
            device.mailbox_managed = device_raw.get('mailboxManaged')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Maas360 Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.MDM]
