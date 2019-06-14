# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from axonius.utils.parsing import normalize_var_name
from netbox_adapter.connection import NetboxConnection
from netbox_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class NetboxAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        device_site = Field(str, 'Site')
        device_display_name = Field(str, 'Display Name')
        device_status = Field(str, 'Status')
        device_type = Field(str, 'Type')
        device_role = Field(str, 'Role')
        device_rack = Field(str, 'Rack')
        device_cluster = Field(str, 'Cluster')
        device_comments = Field(str, 'Comments')
        device_tags = ListField(str, 'Netbox Tags')

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
        connection = NetboxConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      token=client_config.get('token'),
                                      https_proxy=client_config.get('https_proxy'))
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
        The schema NetboxAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Netbox Domain',
                    'type': 'string'
                },
                {
                    'name': 'token',
                    'title': 'Authentication Token',
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
            device.id = str(device_id) + '_' + (str(device_raw.get('name')) or '')
            device.name = str(device_raw.get('name'))
            device.device_serial = device_raw.get('serial')
            device.device_display_name = device_raw.get('display_name')
            try:
                device.device_site = (device_raw.get('site') or {}).get('name')
            except Exception:
                logger.exception(f'Could not get site')

            try:
                device.device_type = (device_raw.get('device_type') or {}).get('display_name')
                device.device_manufacturer = (device_raw.get('device_type') or {}).get('manufacturer').get('name')
            except Exception:
                logger.exception(f'Could not get type')

            try:
                device.device_role = (device_raw.get('device_role') or {}).get('name')
            except Exception:
                logger.exception(f'Could not get role')

            try:
                device.device_cluster = (device_raw.get('cluster') or {}).get('name')
            except Exception:
                logger.exception(f'Could not get cluster')

            try:
                device.device_status = (device_raw.get('status') or {}).get('label')
            except Exception:
                logger.exception(f'Could not get status')

            try:
                device.device_comments = device_raw.get('comments')
            except Exception:
                logger.exception(f'Could not get comments')

            try:
                device.device_rack = (device_raw.get('rack') or {}).get('display_name')
            except Exception:
                logger.exception(f'Could not get rack')

            try:
                device.device_tags = device_raw.get('tags')
            except Exception:
                logger.exception(f'Could not get tags')

            ips = []

            for ip_field in ['primary_ip', 'primary_ip4', 'primary_ip6']:
                try:
                    ip = device_raw.get(ip_field)
                    if isinstance(ip, str):
                        if '/' not in ip:
                            ips.append(ip)
                        else:
                            ip, subnet = ip.split('/')
                            if str(subnet) == '32':
                                ips.append(ip)
                except Exception:
                    logger.exception(f'Could not get ip {ip_field}')

            device.add_nic(ips=ips)

            for attribute_raw, attribute_raw_value in device_raw.items():
                try:
                    normalized_column_name = 'netbox_' + normalize_var_name(attribute_raw)
                    if not device.does_field_exist(normalized_column_name):
                        # Currently we treat all columns as str
                        cn_capitalized = ' '.join([word.capitalize() for word in attribute_raw.split(' ')])
                        device.declare_new_field(normalized_column_name, Field(str, f'NetBox {cn_capitalized}'))

                    device[normalized_column_name] = str(attribute_raw_value)
                except Exception:
                    logger.exception(f'Problem adding attribute {attribute_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Netbox Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
