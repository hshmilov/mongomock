import logging
import urllib.parse

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date, _parse_unix_timestamp
from axonius.mixins.configurable import Configurable
from mobileiron_adapter.connection import MobileironConnection

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-instance-attributes
class MobileironAdapter(AdapterBase, Configurable):

    class MyDeviceAdapter(DeviceAdapter):
        user_id = Field(str, 'Device User Id')
        imei = Field(str, 'Device IMEI')
        storage_capacity = Field(str, 'Storage Capacity')
        user_email = Field(str, 'User Email')
        imsi = Field(str, 'Device IMSI')
        current_phone_number = Field(str, 'Current phone number')
        user_first_name = Field(str, 'User First Name')
        user_last_name = Field(str, 'User Last Name')
        device_encrypted = Field(bool, 'Device Encrypted')
        device_is_compromised = Field(bool, 'Device Is Compromised')
        health_data_bit_locker_status = Field(bool, 'Bitlocker Status')
        registration_state = Field(str, 'Registration State')
        display_name = Field(str, 'Display Name')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(
            urllib.parse.urljoin(client_config.get('domain'), client_config.get('url_base_path'), '/rest/api/v2/'),
            use_domain_path=True)

    @staticmethod
    def _get_connection_cloud(client_config):
        connection = MobileironConnection(domain=client_config['domain'],
                                          url_base_prefix='api/v1',
                                          verify_ssl=client_config['verify_ssl'],
                                          username=client_config['username'],
                                          password=client_config['password'],
                                          is_cloud=True)
        return connection

    @staticmethod
    def _get_connection_core(client_config):
        connection = MobileironConnection(domain=client_config['domain'],
                                          url_base_prefix=client_config.get('url_base_path') + '/rest/api/v2/',
                                          verify_ssl=client_config['verify_ssl'],
                                          username=client_config['username'],
                                          password=client_config['password'],
                                          is_cloud=False)
        return connection

    def _connect_client(self, client_config):
        try:
            is_cloud = client_config.get('is_cloud') or False
            if is_cloud:
                connection = self._get_connection_cloud(client_config)
            else:
                connection = self._get_connection_core(client_config)
            with connection:
                pass  # check that the connection credentials are valid
            return connection, is_cloud
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Mobileiron domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a MobileIron connection

        :return: A json with all the attributes returned from the MobileIron Server
        """
        connection, is_cloud = client_data
        with connection:
            for raw_data in connection.get_device_list(fetch_apps=self.__fetch_apps, is_cloud=is_cloud):
                device_raw, users_list = raw_data
                yield device_raw, users_list, is_cloud

    @staticmethod
    def _clients_schema():
        """
        The schema MobileIronAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'MobileIron Domain',
                    'type': 'string'
                },
                {
                    'name': 'is_cloud',
                    'title': 'Is MobileIron Cloud',
                    'type': 'bool'
                },
                {
                    'name': 'url_base_path',
                    'title': 'URL Base Path (For MobileIron Core)',
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
                }
            ],
            'required': [
                'domain',
                'is_cloud',
                'username',
                'password',
                'verify_ssl',
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_core_device(self, device_raw, users_dict):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('common.id')
            if not device_id:
                logger.warning(f'Bad device with not id')
                return None
            # I hope this is fine, I don't want to change it since we have devices in customers
            device.id = device_id
            device.uuid = device_raw.get('common.uuid')
            device.hostname = device_raw.get('ios.DeviceName', '')
            device.figure_os(device_raw.get('common.platform'))
            device.os.distribution = device_raw.get('common.os_version')
            try:
                ips = device_raw.get('common.ip_address')
                if not ips or 'null' in device_raw.get('common.ip_address'):
                    ips = []
                else:
                    ips = ips.split(',')
                ether_mac = device_raw.get('common.ethernet_mac')
                wifi_mac = device_raw.get('common.wifi_mac_address')
                if not wifi_mac or 'null' in wifi_mac:
                    wifi_mac = None
                if not ether_mac or 'null' in ether_mac:
                    ether_mac = None
                if ether_mac and wifi_mac:
                    macs = [ether_mac, wifi_mac]
                elif ether_mac or wifi_mac:
                    macs = [ether_mac or wifi_mac]
                else:
                    macs = []
                if macs or ips:
                    device.add_ips_and_macs(macs, ips)
            except Exception:
                logger.exception(f'Problem adding nic to a device {device_raw}')
            device.add_agent_version(agent=AGENT_NAMES.mobileiron, version=device_raw.get('common.client_version'))
            device.device_model = device_raw.get('common.model')
            try:
                device.security_patch_level = parse_date(device_raw.get('android.security_patch'))
            except Exception:
                logger.exception(f'Problem getting security patch levle for {device_raw}')
            device.user_id = device_raw.get('user.user_id')
            try:
                user_raw = users_dict.get(device_raw.get('user.user_id'))
                if user_raw:
                    device.user_first_name = user_raw.get('firstName')
                    device.user_last_name = user_raw.get('lastName')
            except Exception:
                logger.exception(f'Problem getting more users data')
            try:
                last_seen = parse_date(device_raw.get('common.miclient_last_connected_at'))
                if not last_seen:
                    last_seen = parse_date(device_raw.get('common.last_connected_at'))
                if self.__exclude_no_last_seen_devices and not last_seen:
                    return None
                device.last_seen = last_seen
            except Exception:
                logger.exception(f'Problem adding last seen to {device_raw}')
            device.imei = device_raw.get('common.imei')
            device.storage_capacity = str(device_raw.get('common.storage_capacity'))
            device.user_email = device_raw.get('user.email_address')
            device.current_phone_number = device_raw.get('common.current_phone_number')
            device.imsi = device_raw.get('common.imsi')
            device.device_encrypted = bool(device_raw.get('common.device_encrypted'))
            device.device_is_compromised = bool(device_raw.get('common.device_is_compromised'))
            health_data_bit_locker_status = device_raw.get('windows_phone.health_data_bit_locker_status')
            if isinstance(health_data_bit_locker_status, str):
                device.health_data_bit_locker_status = health_data_bit_locker_status == '1'
            try:
                if device_raw.get('appInventory') and isinstance(device_raw.get('appInventory'), list):
                    for app in device_raw.get('appInventory'):
                        try:
                            device.add_installed_software(name=app['name'], version=app['version'])
                        except Exception:
                            logger.exception(f'Problem with app {app}')
            except Exception:
                logger.exception(f'Problem adding apps to a decvice {device_raw}')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching MobileIron Device {device_raw}')
            return None

    def _create_cloud_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            if device_raw.get('id') is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_raw.get('id')) + '_' + (device_raw.get('deviceName') or '')
            device.name = device_raw.get('deviceName')
            device.current_phone_number = device_raw.get('phoneNumber')
            device.device_model = device_raw.get('deviceModel')
            if device_raw.get('lastCheckin'):
                device.last_seen = _parse_unix_timestamp(device_raw.get('lastCheckin'))
            device.registration_state = device_raw.get('registrationState')
            device.figure_os((device_raw.get('prettyModel') or '') + ' ' +
                             (device_raw.get('platformType') or '') + ' ' +
                             (device_raw.get('platformVersion') or ''))
            device.device_serial = device_raw.get('serialNumber')
            device.add_nic(mac=device_raw.get('wifiMacAddress'))
            device.imsi = device_raw.get('imsi')
            device.device_manufacturer = device_raw.get('manufacturer')
            device.add_agent_version(agent=AGENT_NAMES.mobileiron, version=device_raw.get('clientVersion'))
            device.user_email = device_raw.get('emailAddress')
            device.user_last_name = device_raw.get('lastName')
            device.display_name = device_raw.get('displayName')
            device.user_first_name = device_raw.get('firstName')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem parsing cloud device {device_raw}')

    # pylint: disable=R1702,R0912,R0915
    def _parse_raw_data(self, devices_raw_data):
        for device_raw, users_dict, is_cloud in devices_raw_data:
            if not is_cloud:
                device = self._create_core_device(device_raw, users_dict)
            else:
                device = self._create_cloud_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.MDM]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_apps',
                    'title': 'Fetch Applications',
                    'type': 'bool'
                },
                {
                    'name': 'exclude_no_last_seen_devices',
                    'title': 'Exclude No Last Seen Devices',
                    'type': 'bool'
                }
            ],
            'required': [
                'fetch_apps',
                'exclude_no_last_seen_devices'
            ],
            'pretty_name': 'Mobileiron Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_apps': True,
            'exclude_no_last_seen_devices': False
        }

    def _on_config_update(self, config):
        self.__fetch_apps = config['fetch_apps']
        self.__exclude_no_last_seen_devices = config['exclude_no_last_seen_devices']
