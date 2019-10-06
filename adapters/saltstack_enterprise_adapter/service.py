import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from saltstack_enterprise_adapter.client_id import get_client_id
from saltstack_enterprise_adapter.connection import \
    SaltstackEnterpriseConnection
from saltstack_enterprise_adapter.consts import DEFAULT_CONFIG_NAME

logger = logging.getLogger(f'axonius.{__name__}')


class SaltstackEnterpriseAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        saltversion = Field(str, 'Salt Version')

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
        connection = SaltstackEnterpriseConnection(domain=client_config['domain'],
                                                   verify_ssl=client_config['verify_ssl'],
                                                   https_proxy=client_config.get('https_proxy'),
                                                   username=client_config['username'],
                                                   password=client_config['password'],
                                                   config_name=client_config.get('config_name') or DEFAULT_CONFIG_NAME)
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
        The schema SaltstackAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Saltstack Enterprise Domain',
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
                    'name': 'config_name',
                    'title': 'Config Name',
                    'type': 'string',
                    'default': DEFAULT_CONFIG_NAME,
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
                'config_name',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            if 'grains' not in device_raw or isinstance(device_raw['grains'], list):
                raise RuntimeError('missing grains')
            device_raw = device_raw['grains']

            device = self._new_device_adapter()
            device.id = device_raw['id']
            device.set_raw(device_raw)
            device.hostname = device_raw.get('fqdn') or device_raw.get()
            try:
                device.figure_os((device_raw.get('kernel') or '') + ' ' + (device_raw.get('osfullname') or ''))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            macs = []
            try:
                for mac in device_raw.get('hwaddr_interfaces').values():
                    if mac and mac != '00:00:00:00:00:00':
                        macs.append(mac)
            except Exception:
                logger.exception(f'Problem getting macs for {device_raw}')
            ips = []
            try:
                for ips_list_name, ips_list in device_raw.get('ip_interfaces').items():
                    if ips_list and ips_list_name != 'lo' and isinstance(ips_list, list):
                        ips.extend(ips_list)
            except Exception:
                logger.exception(f'Problem getting macs for {device_raw}')
            device.add_ips_and_macs(macs, ips)
            device.device_serial = device_raw.get('serialnumber')
            try:
                if isinstance(device_raw.get('username'), str):
                    device.last_used_users = device_raw.get('username').split(',')
            except Exception:
                logger.exception(f'Problem getting users for {device_raw}')
            device.saltversion = device_raw.get('saltversion')
            return device
        except Exception:
            logger.exception(f'Problem with fetching SaltstackEnterprise Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
