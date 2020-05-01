import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.fields import Field
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.mixins.configurable import Configurable
from axonius.plugin_base import add_rule, return_error, EntityType
from axonius.utils.datetime import parse_date
from axonius.clients.cherwell.connection import CherwellConnection
from cherwell_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class CherwellAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        bus_ob_id = Field(str, 'Bus Ob ID')
        bus_ob_rec_id = Field(str, 'BusObRecId')
        bus_ob_public_id = Field(str, 'BusObPublicId')
        ci_type_name = Field(str, 'CI Type Name')
        created_by = Field(str, 'Created By')
        asset_tag = Field(str, 'Asset Tag')
        last_modified = Field(datetime.datetime, 'Last Modification')
        asset_status = Field(str, 'Asset Status')
        location_building = Field(str, 'Location Building')
        primary_full_user_name = Field(str, 'Primary Full User Name')
        asset_type = Field(str, 'Asset Type')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @add_rule('update_computer', methods=['POST'])
    def create_cherwell_computer(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        cherwell_connection = self.get_request_data_as_object()
        success = False
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status, device_raw = conn.update_cherwell_computer(cherwell_connection)
                    success = success or result_status
                    if success is True:
                        device = self._create_device(device_raw=device_raw)
                        if device:
                            device_dict = device.to_dict()
                            self._save_data_from_plugin(
                                client_id,
                                {'raw': [], 'parsed': [device_dict]},
                                EntityType.Devices, False)
                            self._save_field_names_to_db(EntityType.Devices)
                        return '', 200
            except Exception:
                logger.exception(f'Could not connect to {client_id}')
        return 'Failure', 400

    @add_rule('create_incident', methods=['POST'])
    def create_cherwell_incident(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        cherwell_connection = self.get_request_data_as_object()
        success = False
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status = conn.create_incident(cherwell_connection)
                    success = success or result_status
                    if success is True:
                        return '', 200
            except Exception:
                logger.exception(f'Could not connect to {client_id}')
        return 'Failure', 400

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = CherwellConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        username=client_config['username'],
                                        password=client_config['password'],
                                        client_id=client_config['client_id'])
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
        The schema CherwellAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cherwell Domain',
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
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
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
                'client_id',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def _create_device(self, device_raw):
        try:
            device_response = device_raw.get('responses')[0]
            device = self._new_device_adapter()
            device.id = (device_response.get('busObId') or '') + '_' + (device_response.get('busObRecId') or '')
            device.bus_ob_id = device_response.get('busObId')
            device.bus_ob_rec_id = device_response.get('busObRecId')
            device.bus_ob_public_id = device_response.get('busObPublicId')
            mac = None
            ips = None
            for field_raw in device_response.get('fields'):
                try:
                    field_name = field_raw.get('name')
                    field_value = field_raw.get('value')
                    if not field_name or not field_value:
                        continue
                    if field_name == 'SerialNumber':
                        device.device_serial = field_value
                        device.id += '_' + field_value
                    elif field_name == 'AssetType':
                        device.asset_type = field_value
                    elif field_name == 'Model':
                        device.device_model = field_value
                    elif field_name == 'BIOSVersion':
                        device.bios_version = field_value
                    elif field_name == 'UserName':
                        device.last_used_users = [field_value]
                    elif field_name == 'OperatingSystem':
                        device.figure_os(field_value)
                    elif field_name == 'MACAddress':
                        mac = field_value
                    elif field_name == 'IPAddress':
                        ips = [field_value]
                    elif field_name == 'NumberCPUs':
                        # pylint: disable=invalid-name
                        device.total_number_of_physical_processors = field_value
                    elif field_name == 'ConfigurationItemTypeName':
                        ci_type_name = field_value
                        if ci_type_name and self.__ci_type_name_white_list \
                                and ci_type_name not in self.__ci_type_name_white_list:
                            return None
                        device.ci_type_name = ci_type_name
                    elif field_name == 'CreatedDateTime':
                        device.first_seen = parse_date(field_value)
                    elif field_name == 'CreatedBy':
                        device.created_by = field_value
                    elif field_name == 'LastModifiedDateTime':
                        device.last_modified = parse_date(field_value)
                    elif field_name == 'Manufacturer':
                        device.device_manufacturer = field_value
                    elif field_name == 'Description':
                        device.description = field_value
                    elif field_name == 'AssetTag':
                        device.asset_tag = field_value
                    elif field_name == 'HostName':
                        device.hostname = field_value
                    elif field_name == 'AssetStatus':
                        device.asset_status = field_value
                    elif field_name == 'AssetOwner':
                        device.owner = field_value
                    elif field_name == 'PrimaryUserName':
                        device.primary_full_user_name = field_value
                    elif field_name == 'LocationBuilding':
                        device.location_building = field_value
                except Exception:
                    logger.exception(f'Problem with field {field_raw}')
            if ips or mac:
                device.add_nic(ips=ips, mac=mac)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Cherwell Device for {device_raw}')
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
                    'name': 'ci_type_name_white_list',
                    'title': 'CI type name whitelist',
                    'type': 'string'
                }
            ],
            'required': [],
            'pretty_name': 'Cherwell Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'ci_type_name_white_list': None
        }

    def _on_config_update(self, config):
        self.__ci_type_name_white_list = config.get('ci_type_name_white_list').split(',') \
            if config.get('ci_type_name_white_list') else None
