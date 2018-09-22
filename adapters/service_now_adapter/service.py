import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.service_now.connection import ServiceNowConnection
from axonius.clients.service_now.consts import *
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.plugin_base import add_rule, return_error
from axonius.utils.files import get_local_config_file

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        table_type = Field(str, 'Table Type')
        class_name = Field(str, 'Class Name')
        owner = Field(str, 'Owner')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = ServiceNowConnection(
                domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                username=client_config['username'],
                password=client_config['password'], https_proxy=client_config.get('https_proxy'))
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
            return return_error('Medhod not supported', 405)
        service_now_dict = self.get_request_data_as_object()
        success = False
        for client_id in self._clients:
            # Note that we are assuming this connection is not open since this function will run in a post correlator
            # stage. If this function will be called while in a cycle, the cycle will stop (socket will be closed..)
            # TODO: Change that to use a get_session (a copy of the connection)
            with self._clients[client_id]:
                success = success or self._clients[client_id].\
                    create_service_now_computer(service_now_dict)
                if success is True:
                    return '', 200
        return 'Failure', 400

    def _parse_raw_data(self, devices_raw_data):
        for table_devices_data in devices_raw_data:
            users_table_dict = table_devices_data.get(USERS_TABLE_KEY)
            for device_raw in table_devices_data[DEVICES_KEY]:
                try:
                    device = self._new_device_adapter()
                    device_id = device_raw.get('sys_id')
                    if not device_id:
                        logger.warning(f'Problem getting id at {device_raw}')
                        continue
                    device.id = str(device_id)
                    device.table_type = table_devices_data[DEVICE_TYPE_NAME_KEY]
                    name = device_raw.get('name')
                    device.name = name
                    device.class_name = device_raw.get('sys_class_name')
                    try:
                        ip_addresses = device_raw.get('ip_address')
                        if ip_addresses and not any(elem in ip_addresses for elem in ['DHCP',
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
                    owned_by = users_table_dict.get((device_raw.get('owned_by') or {}).get('value'))
                    if owned_by:
                        device.owner = owned_by.get('name')
                    device.set_raw(device_raw)
                    yield device
                except Exception:
                    logger.exception(f'Problem with fetching ServiceNow Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
