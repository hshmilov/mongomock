import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.datetime import parse_date
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.service_now.connection import ServiceNowConnection
from axonius.clients.service_now.consts import *
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.types.correlation import CorrelationResult, CorrelationReason
from axonius.plugin_base import add_rule, return_error, EntityType
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.mixins.configurable import Configurable
logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowAdapter(AdapterBase, Configurable):
    class MyUserAdapter(UserAdapter):
        snow_source = Field(str, 'ServiceNow Source')
        snow_roles = Field(str, 'Roles')

    class MyDeviceAdapter(DeviceAdapter):
        table_type = Field(str, 'Table Type')
        class_name = Field(str, 'Class Name')
        owner = Field(str, 'Owner')
        discovery_source = Field(str, 'Discovery Source')
        last_discovered = Field(datetime.datetime, 'Last Discovered')
        first_discovered = Field(datetime.datetime, 'First Discovered')
        snow_location = Field(str, 'Location')
        snow_department = Field(str, 'Department')
        assigned_to = Field(str, 'Assigned To')
        install_status = Field(str, 'Install Status')
        assigned_to_location = Field(str, 'Assigned To Location')
        purchase_date = Field(datetime.datetime, 'Purchase date')
        substatus = Field(str, 'Substatus')
        u_shared = Field(str, 'Shared')
        u_loaner = Field(str, 'Loaner')
        u_casper_status = Field(str, 'Casper Status')
        u_altiris_status = Field(str, 'Altiris Status')
        first_deployed = Field(datetime.datetime, 'First Deployed')
        created_at = Field(datetime.datetime, 'Created At')
        created_by = Field(str, 'Created By')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    # pylint: disable=R0912,R0915,R0914
    def create_snow_device(self,
                           device_raw,
                           table_type='cmdb_ci_computer',
                           snow_location_table_dict=None,
                           fetch_ips=True,
                           snow_department_table_dict=None,
                           users_table_dict=None,
                           snow_alm_asset_table_dict=None):
        if snow_location_table_dict is None:
            snow_location_table_dict = dict()
        if snow_alm_asset_table_dict is None:
            snow_alm_asset_table_dict = dict()
        if users_table_dict is None:
            users_table_dict = dict()
        if snow_department_table_dict is None:
            snow_department_table_dict = dict()
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('sys_id')
            if not device_id:
                logger.warning(f'Problem getting id at {device_raw}')
                return None
            device.id = str(device_id)
            device.table_type = table_type
            name = device_raw.get('name')
            device.name = name
            device.class_name = device_raw.get('sys_class_name')
            try:
                ip_addresses = device_raw.get('ip_address')
                if fetch_ips and ip_addresses and not any(elem in ip_addresses for elem in ['DHCP',
                                                                                            '*',
                                                                                            'Stack',
                                                                                            'x',
                                                                                            'X']):
                    ip_addresses = ip_addresses.split('/')
                    ip_addresses = [ip.strip() for ip in ip_addresses]
                else:
                    ip_addresses = None
                mac_address = device_raw.get('mac_address')
                if mac_address or ip_addresses:
                    device.add_nic(mac_address, ip_addresses)
            except Exception:
                logger.exception(f'Problem getting NIC at {device_raw}')
            device.figure_os(
                (device_raw.get('os') or '') + ' ' + (device_raw.get('os_address_width') or '') + ' ' +
                (device_raw.get('os_domain') or '') +
                ' ' + (device_raw.get('os_service_pack') or '') + ' ' + (device_raw.get('os_version') or ''))
            device_model = None
            try:
                model_number = device_raw.get('model_number')
                if isinstance(model_number, dict):
                    device_model = model_number.get('value')
                    device.device_model = device_model
            except Exception:
                logger.exception(f'Problem getting model at {device_raw}')
            try:
                device_serial = device_raw.get('serial_number')
                if (device_serial or '').startswith('VMware'):
                    device_serial += device_model or ''
                if not any(bad_serial in device_serial for bad_serial in
                           ['Pending Discovery',
                            'Virtual Machine',
                            'VMware Virtual Platform',
                            'AT&T', 'unknown',
                            'Instance']):
                    device.device_serial = device_serial
            except Exception:
                logger.exception(f'Problem getting serial at {device_raw}')
            # pylint: disable=R1714
            try:
                ram_mb = device_raw.get('ram', '')
                if ram_mb != '' and ram_mb != '-1' and ram_mb != -1:
                    device.total_physical_memory = int(ram_mb) / 1024.0
            except Exception:
                logger.exception(f'Problem getting ram at {device_raw}')
            try:
                host_name = device_raw.get('host_name') or device_raw.get('fqdn')
                if host_name and name and name.lower() in host_name.lower():
                    device.hostname = host_name
            except Exception:
                logger.exception(f'Problem getting hostname in {device_raw}')
            device.description = device_raw.get('short_description')
            try:
                snow_department = snow_department_table_dict.get(
                    (device_raw.get('department') or {}).get('value'))
                if snow_department:
                    device.snow_department = snow_department.get('name')
            except Exception:
                logger.exception(f'Problem adding assigned_to to {device_raw}')
            try:
                snow_asset = snow_alm_asset_table_dict.get((device_raw.get('asset') or {}).get('value'))
                if snow_asset:
                    try:
                        device.install_status = INSTALL_STATUS_DICT.get(snow_asset.get('install_status'))
                    except Exception:
                        logger.exception(f'Problem getting install status for {device_raw}')
                    device.u_loaner = snow_asset.get('u_loaner')
                    device.u_shared = snow_asset.get('u_shared')
                    try:
                        device.first_deployed = parse_date(snow_asset.get('u_first_deployed'))
                    except Exception:
                        logger.exception(f'Problem getting first deployed at {device_raw}')
                    device.u_altiris_status = snow_asset.get('u_altiris_status')
                    device.u_casper_status = snow_asset.get('u_casper_status')
                    try:
                        device.substatus = snow_asset.get('substatus')
                    except Exception:
                        logger.exception(f'Problem adding hardware status to {device_raw}')
                    try:
                        device.purchase_date = parse_date(snow_asset.get('purchase_date'))
                    except Exception:
                        logger.exception(f'Problem adding purchase date to {device_raw}')
                    try:
                        snow_location = snow_location_table_dict.get(
                            (snow_asset.get('location') or {}).get('value'))
                        if snow_location:
                            device.snow_location = snow_location.get('name')
                    except Exception:
                        logger.exception(f'Problem adding assigned_to to {device_raw}')
            except Exception:
                logger.exception(f'Problem at asset table information {device_raw}')

            try:
                assigned_to = users_table_dict.get((device_raw.get('assigned_to') or {}).get('value'))
                if assigned_to:
                    device.assigned_to = assigned_to.get('name')
                    try:
                        assigned_to_location_value = (assigned_to.get('location') or {}).get('value')
                        device.assigned_to_location = (snow_location_table_dict.get(
                            assigned_to_location_value) or {}).get('name')
                    except Exception:
                        logger.exception(f'Problem getting assing to location in {device_raw}')
            except Exception:
                logger.exception(f'Problem adding assigned_to to {device_raw}')
            owned_by = users_table_dict.get((device_raw.get('owned_by') or {}).get('value'))
            if owned_by:
                device.owner = owned_by.get('name')
            try:
                device.device_manufacturer = device_raw.get('cpu_manufacturer')
                ghz = device_raw.get('cpu_speed')
                if ghz:
                    ghz = float(ghz) / 1024.0
                else:
                    ghz = None
                device.add_cpu(name=device_raw.get('cpu_name'),
                               cores=int(device_raw.get('cpu_count'))
                               if device_raw.get('cpu_count') else None,
                               cores_thread=int(device_raw.get('cpu_core_thread'))
                               if device_raw.get('cpu_core_thread') else None,
                               ghz=ghz)
            except Exception:
                logger.exception(f'Problem adding cpu stuff to {device_raw}')
            try:
                device.discovery_source = device_raw.get('discovery_source')
                device.first_discovered = parse_date(device_raw.get('first_discovered'))
                device.last_discovered = parse_date(device_raw.get('last_discovered'))
                device.created_at = parse_date((device_raw.get('sys_created_on')))
                device.created_by = device_raw.get('sys_created_by')
            except Exception:
                logger.exception(f'Problem addding source stuff to {device_raw}')
            try:
                if device_raw.get('disk_space'):
                    device.add_hd(total_size=float(device_raw.get('disk_space')))
            except Exception:
                logger.exception(f'Problem adding disk stuff to {device_raw}')
            device.domain = device_raw.get('dns_domain')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching ServiceNow Device {device_raw}')
            return None

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            https_proxy = client_config.get('https_proxy')
            if https_proxy and https_proxy.startswith('http://'):
                https_proxy = 'https://' + https_proxy[len('http://'):]
            connection = ServiceNowConnection(
                domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                username=client_config['username'],
                password=client_config['password'], https_proxy=https_proxy)
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
        Get all devices from a specific ServiceNow domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a ServiceNow connection

        :return: A json with all the attributes returned from the ServiceNow Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _query_users_by_client(self, key, data):
        if self.__fetch_users:
            yield from data.get_user_list()
        else:
            yield from []

    def _clients_schema(self):
        """
        The schema ServiceNowAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'ServiceNow Domain',
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
                'verify_ssl'
            ],
            'type': 'array'
        }

    @add_rule('create_incident', methods=['POST'])
    def create_service_now_incident(self):
        if self.get_method() != 'POST':
            return return_error('Medhod not supported', 405)
        service_now_dict = self.get_request_data_as_object()
        success = False
        for client_id in self._clients:
            # Note that we are assuming this connection is not open since this function will run in a post correlator
            # stage. If this function will be called while in a cycle, the cycle will stop (socket will be closed..)
            # TODO: Change that to use a get_session (a copy of the connection)
            with self._clients[client_id]:
                success = success or self._clients[client_id].create_service_now_incident(service_now_dict)
                if success is True:
                    return '', 200
        return 'Failure', 400

    @add_rule('create_computer', methods=['POST'])
    def create_service_now_computer(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        request_json = self.get_request_data_as_object()
        service_now_dict = request_json.get('snow')
        success = False
        for client_id in self._clients:
            # Note that we are assuming this connection is not open since this function will run in a post correlator
            # stage. If this function will be called while in a cycle, the cycle will stop (socket will be closed..)
            # TODO: Change that to use a get_session (a copy of the connection)
            with self._clients[client_id]:
                result_status, device_raw = self._clients[client_id].create_service_now_computer(service_now_dict)
                success = success or result_status
                if success is True:
                    device = self.create_snow_device(device_raw=device_raw,
                                                     fetch_ips=self.__fetch_ips,
                                                     table_type='cmdb_ci_computer')
                    if device:
                        device_id = device.id
                        device_dict = device.to_dict()
                        self._save_data_from_plugin(
                            client_id,
                            {'raw': [], 'parsed': [device_dict]},
                            EntityType.Devices, False)
                        to_correlate = request_json.get('to_ccorrelate')
                        if isinstance(to_correlate, dict):
                            to_correlate_plugin_unique_name = to_correlate.get('to_correlate_plugin_unique_name')
                            to_correlate_device_id = to_correlate.get('device_id')
                            if to_correlate_plugin_unique_name and to_correlate_device_id:
                                correlation_param = CorrelationResult(associated_adapters=[(to_correlate_plugin_unique_name,
                                                                                            to_correlate_device_id),
                                                                                           (self.plugin_unique_name, device_id)],
                                                                      data={'reason': 'ServiceNow Device Creation'},
                                                                      reason=CorrelationReason.ServiceNowCreation)
                                self.link_adapters(EntityType.Devices, correlation_param)
                    return '', 200
        return 'Failure', 400

    def _parse_users_raw_data(self, raw_data):
        for user_raw in raw_data:
            try:
                user = self._new_user_adapter()
                sys_id = user_raw.get('sys_id')
                if not sys_id:
                    logger.warning(f'Bad user with no id {user_raw}')
                    continue
                user.id = sys_id
                user.mail = user_raw.get('email')
                user.employee_number = user_raw.get('employee_number')
                user.user_country = user_raw.get('country')
                user.first_name = user_raw.get('first_name')
                user.last_name = user_raw.get('last_name')
                user.username = user_raw.get('name')
                user.user_title = user_raw.get('title')
                try:
                    user.user_manager = (user_raw.get('manager_full') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting manager for {user_raw}')
                user.snow_source = user_raw.get('source')
                user.snow_roles = user_raw.get('roles')
                user.user_telephone_number = user_raw.get('phone')
                user.set_raw(user_raw)
                yield user
            except Exception:
                logger.exception(f'Problem getting user {user_raw}')

    def _parse_raw_data(self, devices_raw_data):
        for table_devices_data in devices_raw_data:
            users_table_dict = table_devices_data.get(USERS_TABLE_KEY)
            snow_department_table_dict = table_devices_data.get(DEPARTMENT_TABLE_KEY)
            snow_location_table_dict = table_devices_data.get(LOCATION_TABLE_KEY)
            snow_alm_asset_table_dict = table_devices_data.get(ALM_ASSET_TABLE)
            for device_raw in table_devices_data[DEVICES_KEY]:
                device = self.create_snow_device(device_raw=device_raw,
                                                 snow_department_table_dict=snow_department_table_dict,
                                                 snow_location_table_dict=snow_location_table_dict,
                                                 snow_alm_asset_table_dict=snow_alm_asset_table_dict,
                                                 users_table_dict=users_table_dict,
                                                 fetch_ips=self.__fetch_ips,
                                                 table_type=table_devices_data[DEVICE_TYPE_NAME_KEY])
                if device:
                    yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    'name': 'fetch_users',
                    'type': 'bool',
                    'title': 'Should Fetch Users'
                },
                {
                    'name': 'fetch_ips',
                    'type': 'bool',
                    'title': 'Should Fetch IPs'
                }
            ],
            "required": [
                'fetch_users',
                'fetch_ips'
            ],
            "pretty_name": "ServiceNow Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_users': True,
            'fetch_ips': True
        }

    def _on_config_update(self, config):
        self.__fetch_users = config['fetch_users']
        self.__fetch_ips = config['fetch_ips']
