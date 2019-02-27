import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.plugin_base import add_rule, return_error
from axonius.utils.parsing import normalize_var_name
from axonius.clients.sysaid.connection import SysaidConnection
from sysaid_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SysaidAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        group = Field(str, 'Group')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @add_rule('create_incident', methods=['POST'])
    def create_sysaid_incident_in_adapter(self):
        if self.get_method() != 'POST':
            return return_error('Medhod not supported', 405)
        sysaid_dict = self.get_request_data_as_object()
        success = False
        for client_id in self._clients:
            conn = self.get_connection(self._get_client_config_by_client_id(client_id))
            with conn:
                success = success or conn.create_sysaid_incident(sysaid_dict)
                if success is True:
                    return '', 200
        return 'Failure', 400

    @staticmethod
    def get_connection(client_config):
        with SysaidConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                              username=client_config['username'], password=client_config['password']) as connection:
            return connection

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

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
        The schema SysaidAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Sysaid Domain',
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
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        # pylint: disable=R1702
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('name') or '')
                device.hostname = device_raw.get('name')
                device.group = device_raw.get('group')
                device_info = device_raw.get('info')
                if not device_info:
                    device_info = []
                for key_info in device_info:
                    try:
                        if key_info.get('key') == 'serial':
                            device.device_serial = key_info.get('value')
                        elif key_info.get('key') == 'ip_address' and key_info.get('value'):
                            device.add_nic(None, [key_info.get('value')])
                        elif key_info.get('key'):
                            normalized_column_name = 'sysaid_' + normalize_var_name(key_info.get('key'))
                            if not device.does_field_exist(normalized_column_name):
                                cn_capitalized = ' '.join([word.capitalize()
                                                           for word in key_info.get('key').split(' ')])
                                device.declare_new_field(normalized_column_name, Field(str, f'Sysaid {cn_capitalized}'))
                            device[normalized_column_name] = key_info.get('value')
                    except Exception:
                        logger.exception(f'Problem with key info {key_info}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Sysaid Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
