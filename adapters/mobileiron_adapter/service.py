import logging
import urllib.parse

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from axonius.mixins.configurable import Configurable
from mobileiron_adapter.connection import MobileironConnection

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-instance-attributes
class MobileironAdapter(AdapterBase, Configurable):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        user_id = Field(str, 'Device User Id')
        imei = Field(str, 'Device IMEI')
        storage_capacity = Field(str, 'Storage Capacity')
        user_email = Field(str, 'User Email')
        imsi = Field(str, 'Device IMSI')
        uuid = Field(str, 'Device UUID')
        current_phone_number = Field(str, 'Current phone number')

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
    def _connect_client(client_config):
        try:
            connection = MobileironConnection(domain=client_config['domain'],
                                              headers={'Content-Type': 'application/json',
                                                       'Accept': 'application/json'},
                                              url_base_prefix=client_config.get('url_base_path') + '/rest/api/v2/',
                                              verify_ssl=client_config['verify_ssl'],
                                              username=client_config['username'],
                                              password=client_config['password'])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
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
        with client_data:
            yield from client_data.get_device_list(fetch_apps=self.__fetch_apps)

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
                    'name': 'url_base_path',
                    'title': 'URL Base Path',
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
                'username',
                'password',
                'verify_ssl',
                'url_base_path'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.id = device_raw.get('common.id')
                if device.id is None:
                    continue
                device.uuid = device_raw.get('common.uuid')
                device.hostname = device_raw.get('ios.DeviceName',  '')
                device.figure_os(device_raw.get('common.platform', ''))
                device.os.type = device_raw.get('common.platform', '')
                device.os.distribution = device_raw.get('common.os_version', '')
                try:
                    if device_raw.get('common.ethernet_mac')or device_raw.get('common.ip_address'):
                        device.add_nic(device_raw.get('common.wifi_mac_address'), device_raw.get(
                            'common.ip_address', '').split(','))
                except Exception:
                    logger.exception('Problem adding nic to a device')
                device.agent_version = device_raw.get('common.client_version', '')
                device.device_model = device_raw.get('common.model')
                try:
                    device.security_patch_level = parse_date(device_raw.get('android.security_patch'))
                except Exception:
                    logger.exception(f'Problem getting security patch levle for {device_raw}')
                device.user_id = device_raw.get('user.user_id')
                device.last_seen = parse_date(device_raw.get('common.miclient_last_connected_at', ''))
                device.imei = device_raw.get('common.imei')
                device.storage_capacity = str(device_raw.get('common.storage_capacity'))
                device.user_email = device_raw.get('user.email_address')
                device.current_phone_number = device_raw.get('common.current_phone_number')
                device.imsi = device_raw.get('common.imsi')
                try:
                    for app in device_raw.get('appInventory', []):
                        device.add_installed_software(name=app['name'], version=app['version'])
                except Exception:
                    logger.exception('Problem adding apps to a decvice')

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception('Problem with fetching MobileIron Device')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_apps',
                    'title': 'Fetch Applications',
                    'type': 'bool'
                }
            ],
            'required': [
                'fetch_apps'
            ],
            'pretty_name': 'Mobileiron Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_apps': True
        }

    def _on_config_update(self, config):
        self.__fetch_apps = config['fetch_apps']
