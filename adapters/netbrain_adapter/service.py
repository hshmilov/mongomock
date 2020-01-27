import logging

from axonius.utils.parsing import format_ip, format_ip_raw

from axonius.fields import Field, JsonStringFormat
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from netbrain_adapter.connection import NetbrainConnection
from netbrain_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class NetbrainAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        mgmt_ip = Field(str, 'Management IP', converter=format_ip, json_format=JsonStringFormat.ip)
        mgmt_ip_raw = Field(str, converter=format_ip_raw)

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = NetbrainConnection(
            auth_id=client_config.get('auth_id'),
            tenant_id=client_config['tenant_id'],
            domain_id=client_config['domain_id'],
            domain=client_config['domain'],
            verify_ssl=client_config['verify_ssl'],
            https_proxy=client_config.get('https_proxy'),
            username=client_config['username'],
            password=client_config['password']
        )
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

    # pylint: disable=C0330
    @staticmethod
    def _clients_schema():
        """
        The schema NetbrainAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'NetBrain Web API Server Host',
                    'type': 'string'
                },
                {
                    # This parameter is only required for an external user through LDAP/AD or TACACS
                    # and the value must match with the name of external authentication which the user
                    # created with admin role during system management under "User Account" section.
                    'name': 'auth_id',
                    'title': 'External Authentication ID',
                    'type': 'string'
                },
                {
                    'name': 'domain_id',
                    'title': 'NetBrain Domain ID',
                    'type': 'string'
                },
                {
                    'name': 'tenant_id',
                    'title': 'NetBrain Tenant ID',
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
                'verify_ssl',
                'domain_id',
                'tenant_id'
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
            # generic stuff
            device.id = f'{device_id}_{device_raw.get("hostname") or ""}'
            device.hostname = device_raw.get('hostname')
            device.description = device_raw.get('deviceTypeName')
            # set first and last seen if possible
            first_seen = parse_date(device_raw.get('firstDiscoverTime'))
            last_seen = parse_date(device_raw.get('lastDiscoverTime'))
            device.first_seen = parse_date(first_seen)
            device.last_seen = parse_date(last_seen)
            # add ip
            try:
                device.add_ips_and_macs(ips=device_raw.get('mgmtIP'))
                device.mgmt_ip = device_raw.get('mgmtIP')
                device.mgmt_ip_raw = device_raw.get('mgmtIP')
            except Exception as e:
                message = f'No IP for {device_raw}'
                logger.exception(message)
                # Silence exception
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Netbrain Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Network]
