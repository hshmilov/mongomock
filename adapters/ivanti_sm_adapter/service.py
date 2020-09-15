import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.clients.ivanti_sm.connection import IvantiSmConnection
from axonius.types.correlation import CorrelationResult, CorrelationReason
from axonius.plugin_base import add_rule, return_error, EntityType
from ivanti_sm_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class IvantiSmAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        rec_id = Field(str, 'Record ID')
        last_modified_time = Field(datetime.datetime, 'Last Modified Time')
        agent_status = Field(str, 'Agent Status')

    class MyUserAdapter(UserAdapter):
        company = Field(str, 'Company')

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
        connection = IvantiSmConnection(domain=client_config['domain'],
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
        The schema IvantiSmAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Ivanti Service Manager Domain',
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

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('RecId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('Name') or '')
            device.rec_id = device_id
            device.agent_status = device_raw.get('AgentStatus')
            device.first_seen = parse_date(device_raw.get('CreatedDateTime'))
            device.owner = device_raw.get('Owner')
            device.device_serial = device_raw.get('SerialNumber')
            device.description = device_raw.get('Description')
            device.figure_os(device_raw.get('OperatingSystem'))
            device.device_manufacturer = device_raw.get('Manufacturer')
            device.name = device_raw.get('Name')
            mac = device_raw.get('MACAddress')
            if not mac:
                mac = None
            ip = device_raw.get('IPAddress')
            if ip and isinstance(ip, str):
                ips = ip.split(',')
            else:
                ips = None
            if ips or mac:
                device.add_nic(ips=ips, mac=mac)
            device.last_modified_time = parse_date(device_raw.get('LastModDateTime'))
            domain = device_raw.get('DomainName')
            if is_domain_valid(domain):
                device.domain = domain
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching IvantiSm Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @add_rule('update_computer', methods=['POST'])
    def update_ivanti_sm_computer(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        ivanti_connection = self.get_request_data_as_object()
        success = False
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status, device_raw = conn.uptade_ivanti_sm_computer(ivanti_connection)
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

    @add_rule('create_computer', methods=['POST'])
    def create_ivanti_sm_computer(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        request_json = self.get_request_data_as_object()
        ivanti_dict = request_json.get('ivanti')
        success = False
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status, device_raw = conn.create_ivanti_sm_computer(ivanti_dict)
                    success = success or result_status
                    if success is True:
                        device = self._create_device(device_raw=device_raw)
                        if device:
                            device_id = device.id
                            device_dict = device.to_dict()
                            self._save_data_from_plugin(
                                client_id,
                                {'raw': [], 'parsed': [device_dict]},
                                EntityType.Devices, False)
                            self._save_field_names_to_db(EntityType.Devices)
                            to_correlate = request_json.get('to_ccorrelate')
                            if isinstance(to_correlate, dict):
                                to_correlate_plugin_unique_name = to_correlate.get('to_correlate_plugin_unique_name')
                                to_correlate_device_id = to_correlate.get('device_id')
                                if to_correlate_plugin_unique_name and to_correlate_device_id:
                                    assoc_ada = [(to_correlate_plugin_unique_name, to_correlate_device_id),
                                                 (self.plugin_unique_name, device_id)]
                                    correlation_param = CorrelationResult(associated_adapters=assoc_ada,
                                                                          data={'reason': 'Ivanti SM Device Creation'},
                                                                          reason=CorrelationReason.IvantiCreation)
                                    self.link_adapters(EntityType.Devices, correlation_param)
                        return '', 200
            except Exception:
                logger.exception(f'Could not connect to {client_id}')
        return 'Failure', 400

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_users_by_client(key, data):
        with data:
            yield from data.get_user_list()

    def _create_user(self, user_raw):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.get('RecId')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('DisplayName') or '')
            user.username = user_raw.get('DisplayName')
            user.first_name = user_raw.get('FirstName')
            user.last_name = user_raw.get('LastName')
            user.mail = user_raw.get('PrimaryEmail')
            user.company = user_raw.get('Company')
            user.image = user_raw.get('EmployeePhoto')
            user.user_department = user_raw.get('Department')
            user.user_title = user_raw.get('Title')
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching BambooHR user for {user_raw}')
            return None

    def _parse_users_raw_data(self, users_raw_data):
        for user_raw in users_raw_data:
            user = self._create_user(user_raw)
            if user:
                yield user
