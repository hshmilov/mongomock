import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.clients.fresh_service.connection import FreshServiceConnection
from axonius.clients.fresh_service.consts import IMPACT_DICT
from fresh_service_adapter.client_id import get_client_id


logger = logging.getLogger(f'axonius.{__name__}')


class FreshServiceAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        impact = Field(str, 'Impact')
        ci_type_name = Field(str, 'CI Type Name')
        asset_tag = Field(str, 'Asset Tag')
        department_name = Field(str, 'Department')
        business_impact = Field(str, 'Business Impact')
        product_name = Field(str, 'Product Name')
        state_name = Field(str, 'State Name')
        warranty = Field(datetime.datetime, 'Warranty')
        acquisition = Field(datetime.datetime, 'Acquisition')

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
        connection = FreshServiceConnection(domain=client_config['domain'],
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
        The schema FreshServiceAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Freshservice Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
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

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.name = device_raw.get('name')
            device.description = device_raw.get('description')
            ci_type_name = device_raw.get('ci_type_name')
            device.ci_type_name = ci_type_name
            if self.__fresh_service_white_list and \
                    ci_type_name and ci_type_name not in self.__fresh_service_white_list:
                return None
            device.impact = IMPACT_DICT.get(device_raw.get('impact'))
            device.last_seen = parse_date(device_raw.get('updated_at'))
            device.first_seen = parse_date(device_raw.get('created_at'))
            device.asset_tag = device_raw.get('asset_tag')
            device.department_name = device_raw.get('department_name')
            device.business_impact = device_raw.get('business_impact')
            device.product_name = device_raw.get('product_name')
            device.device_manufacturer = device_raw.get('vendor_name')
            device.state_name = device_raw.get('state_name')
            try:
                extra_data_raw = device_raw.get('levelfield_values')
                if not isinstance(extra_data_raw, dict):
                    extra_data_raw = {}
                os_str = ''
                ips = []
                mac = None
                for field_name, field_value in extra_data_raw.items():
                    if not field_value:
                        continue
                    if field_name.startswith('os_'):
                        os_str += ' ' + field_value
                    elif field_name.startswith('warranty_expiry_date_'):
                        device.warranty = parse_date(field_value)
                    elif field_name.startswith('acquisition_date_date_'):
                        device.acquisition = parse_date(field_value)
                    elif field_name.startswith('hostname_'):
                        device.hostname = field_value
                    elif field_name.startswith('serial_number_'):
                        device.device_serial = field_value
                    elif field_name.startswith('last_login_by_'):
                        device.last_used_users = [field_value]
                    elif field_name.startswith('computer_ip_address_'):
                        ips_raw = field_value
                        ips_raw = ips_raw[:ips_raw.find('%')]
                        ips = ips_raw.split(',')
                    elif field_name.startswith('mac_address_'):
                        mac = field_value
                device.figure_os(os_str)
                if ips or mac:
                    device.add_nic(mac=mac, ips=ips)
            except Exception:
                logger.exception(f'Problem getting extra fields for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching FreshService Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fresh_service_white_list',
                    'type': 'string',
                    'title': 'Freshservice CI type whitelist'
                }
            ],
            'required': [],
            'pretty_name': 'Freshservice Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fresh_service_white_list': None
        }

    def _on_config_update(self, config):
        self.__fresh_service_white_list = config.get('fresh_service_white_list').split(',') \
            if config.get('fresh_service_white_list') else None
