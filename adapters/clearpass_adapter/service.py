import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import normalize_var_name
from axonius.mixins.configurable import Configurable
from clearpass_adapter.connection import ClearpassConnection
from clearpass_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ClearpassAdapter(AdapterBase, Configurable):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        endpoint_status = Field(str, 'Endpoint Status')
        spt = Field(str, 'System Posture Token')
        is_conflict = Field(bool, 'Is Conflict')
        is_online = Field(bool, 'Is Online')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with ClearpassConnection(domain=client_config['domain'],
                                     verify_ssl=client_config['verify_ssl'],
                                     client_id=client_config['client_id'], client_secret=client_config['client_secret'],
                                     https_proxy=client_config.get('https_proxy')) as connection:
                return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(self.__get_extended_info)

    @staticmethod
    def _clients_schema():
        """
        The schema ClearpassAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Aruba ClearPass Domain',
                    'type': 'string'
                },
                {
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
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
                'client_secret',
                'client_id',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912,R0915,R1702
    def _create_endpoint_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            mac = device_raw.get('mac_address') or ''
            device_id = str(device_raw.get('id') or '')
            if mac or device_id:
                device.id = f'{device_id}_{mac}'
            else:
                logger.warning(f'Bad device with no id {device_raw}')
                return None
            if mac:
                device.add_nic(mac, None)
            device.description = device_raw.get('description')
            device.endpoint_status = device_raw.get('status')
            endpoint_attributes = device_raw.get('attributes')
            hostname = None
            last_seen = None
            if isinstance(endpoint_attributes, dict):
                try:
                    for column_name, column_value in endpoint_attributes.items():
                        try:
                            normalized_column_name = 'clearpass_' + normalize_var_name(column_name)
                            if not device.does_field_exist(normalized_column_name):
                                # Currently we treat all columns as str
                                cn_capitalized = ' '.join([word.capitalize() for word in column_name.split(' ')])
                                device.declare_new_field(normalized_column_name,
                                                         Field(str, f'Clearpass {cn_capitalized}'))
                            device[normalized_column_name] = column_value
                        except Exception:
                            logger.exception(f'Could not parse column {column_name} with value {column_value}')
                        device.device_serial = endpoint_attributes.get('Serial Number')
                        hostname = endpoint_attributes.get('Display Name')
                        device.hostname = hostname
                        last_seen = parse_date(endpoint_attributes.get('Last Check In'))
                        device.last_seen = last_seen
                except Exception:
                    logger.exception(f'Problem with attributes on {device_raw}')
            extended_info = device_raw.get('extended_info')
            if extended_info:
                try:
                    device.domain = extended_info.get('domain')
                    device.last_used_users = [extended_info.get('user')] if extended_info.get('user') else None
                    device.spt = extended_info.get('spt')
                    try:
                        device.figure_os(extended_info.get('device_category'))
                    except Exception:
                        logger.exception(f'Problem with OS of {device_raw}')
                    device.is_conflict = extended_info.get('is_conflict')
                except Exception:
                    logger.exception(f'Problem adding extend info for {device_raw}')
                try:
                    if not last_seen:
                        last_seen = parse_date(extended_info.get('updated_at'))
                        device.last_seen = last_seen
                except Exception:
                    logger.exception(f'Problem with last seen at {device_raw}')
                device.is_online = extended_info.get('is_online')
            if self.__drop_no_last_seen is True and not last_seen:
                return None
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Clearpass Device for {device_raw}')
            return None

    def _create_network_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            ip_address = device_raw.get('ip_address') or ''
            name = device_raw.get('name') or ''
            if name:
                device.name = name
            device_id = str(device_raw.get('id') or '')
            if name or device_id:
                device.id = f'{device_id}_{name}'
            else:
                logger.warning(f'Bad device with no id {device_raw}')
                return None
            if ip_address:
                device.add_nic(None, [ip_address])
            device.description = device_raw.get('description')
            device.device_manufacturer = device_raw.get('vendor_name')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Clearpass Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == 'endpoint':
                device = self._create_endpoint_device(device_raw)
            elif device_type == 'network-device':
                device = self._create_network_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'get_extended_info',
                    'title': 'Get Extended Agent Information',
                    'type': 'bool'
                },
                {
                    'name': 'drop_no_last_seen',
                    'title': 'Do not fetch Devices without Last Seen',
                    'type': 'bool'
                }
            ],
            'required': [
                'get_extended_info',
                'drop_no_last_seen'
            ],
            'pretty_name': 'Clearpass Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'get_extended_info': True,
            'drop_no_last_seen': False
        }

    def _on_config_update(self, config):
        self.__get_extended_info = config['get_extended_info']
        self.__drop_no_last_seen = config['drop_no_last_seen']
