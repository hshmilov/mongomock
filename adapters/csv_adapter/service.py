import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import GetDevicesError
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import make_dict_from_csv

logger = logging.getLogger(f'axonius.{__name__}')


class CsvAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        field1 = Field(str, 'Field1')
        field2 = Field(str, 'Field2')
        field3 = Field(str, 'Field3')

    class MyUserAdapter(UserAdapter):
        field1 = Field(str, 'Field1')
        field2 = Field(str, 'Field2')
        field3 = Field(str, 'Field3')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        return client_config

    def _query_users_by_client(self, key, data):
        is_users_csv = data.get('is_users_csv', False)
        if not is_users_csv:
            return None
        csv_data = self._grab_file_contents(data['csv']).decode('utf-8')
        return (make_dict_from_csv(csv_data),
                data.get('display_name') or 'DisplayName', data.get('mail') or 'Mail',
                data.get('domain') or 'Domain',
                data.get('csv_field1'), data.get('csv_field2'),
                data.get('csv_field3'))

    def _query_devices_by_client(self, client_name, client_data):
        is_users_csv = client_data.get('is_users_csv', False)
        if is_users_csv:
            return None
        csv_data = self._grab_file_contents(client_data['csv']).decode('utf-8')
        return (make_dict_from_csv(csv_data),
                client_data.get('csv_name') or 'Name', client_data.get('csv_mac') or 'MAC Address',
                client_data.get('csv_serial') or 'Serial', client_data.get('csv_os') or 'OS',
                client_data.get('csv_field1'), client_data.get('csv_field2'),
                client_data.get('csv_field3'))

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'is_users_csv',
                    'title': 'Users CSV File',
                    'type': 'bool'
                },
                {
                    'name': 'user_id',
                    'title': 'CSV File ID',
                    'type': 'string'
                },
                {
                    'name': 'csv',
                    'title': 'CSV File',
                    'description': 'The binary contents of the csv',
                    'type': 'file'
                },
                {
                    'name': 'csv_name',
                    'title': 'Asset Name Column',
                    'type': 'string'
                },
                {
                    'name': 'csv_mac',
                    'title': 'MAC Address Column',
                    'type': 'string'
                },
                {
                    'name': 'csv_serial',
                    'title': 'Serial Column',
                    'type': 'string'
                },
                {
                    'name': 'csv_os',
                    'title': 'OS Column',
                    'type': 'string'
                },
                {
                    'name': 'mail',
                    'title': 'Mail',
                    'type': 'string'
                },
                {
                    'name': 'domain',
                    'title': 'Domain',
                    'type': 'string'
                },
                {
                    'name': 'display_name',
                    'title': 'Display Name',
                    'type': 'string'
                },
                {
                    'name': 'csv_field1',
                    'title': 'Field1 Column',
                    'type': 'string'
                },
                {
                    'name': 'csv_field2',
                    'title': 'Field2 Column',
                    'type': 'string'
                },
                {
                    'name': 'csv_field3',
                    'title': 'Field3 Column',
                    'type': 'string'
                }
            ],
            'required': [
                'user_id',
                'csv',
            ],
            'type': 'array'
        }

    def _parse_users_raw_data(self, user):
        if user is None:
            return
        csv_data, display_name, mail, domain, csv_field1, csv_field2, csv_field3 = user
        if display_name not in csv_data.fieldnames and mail not in csv_data.fieldnames:
            logger.error(f'Bad fields names{str(csv_data.fieldnames)}')
            raise GetDevicesError('Strong identifier is missing (Mail/Display)')
        for user_raw in csv_data:
            try:
                user_obj = self._new_user_adapter()
                username = user_raw.get(display_name)
                user_mail = user_raw.get(mail)
                user_obj.username = username
                user_obj.mail = user_mail
                user_obj.id = (user_mail or '') + '_' + (username or '')
                user_obj.domain = user_raw.get(domain)
                user_obj.field1 = user_raw.get(csv_field1)
                user_obj.field2 = user_raw.get(csv_field2)
                user_obj.field3 = user_raw.get(csv_field3)
                user_obj.set_raw(user_raw)
                yield user_obj
            except Exception:
                logger.exception(f'Problem adding user: {str(user_raw)}')

    def _parse_raw_data(self, devices_raw_data):
        if devices_raw_data is None:
            return
        csv_data, csv_name, csv_mac, csv_serial, csv_os, csv_field1, csv_field2, csv_field3 = devices_raw_data
        if csv_serial not in csv_data.fieldnames and csv_mac not in csv_data.fieldnames:
            logger.error(f'Bad fields names{str(csv_data.fieldnames)}')
            raise GetDevicesError('Strong identifier is missing (MAC/Serial)')
        for device_raw in csv_data:
            try:
                device = self._new_device_adapter()
                serial = device_raw.get(csv_serial)
                mac_addresses = (device_raw.get(csv_mac) or '').split(',')
                if serial is not None and serial != '':
                    device.device_serial = serial
                    device.id = serial
                elif mac_addresses != [] and mac_addresses[0] != '':
                    device.id = mac_addresses[0]
                else:
                    continue
                device.name = device_raw.get(csv_name)
                for mac_address in mac_addresses:
                    if mac_address != '':
                        device.add_nic(mac_address, None)
                os = device_raw.get(csv_os)
                if os is not None:
                    device.figure_os(os)
                device.field1 = device_raw.get(csv_field1)
                device.field2 = device_raw.get(csv_field2)
                device.field3 = device_raw.get(csv_field3)
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem adding device: {str(device_raw)}')

    def _correlation_cmds(self):
        """
        Figure out the Serial on the computer
        """
        return {
            'Windows': 'wmic bios get serialnumber',
            'OS X': 'system_profiler SPHardwareDataType | grep \'Serial\''
        }

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        correlation_cmd_result = correlation_cmd_result.strip()
        if os_type == 'Windows':
            return correlation_cmd_result.splitlines()[1].strip()
        if os_type == 'OS X':
            return correlation_cmd_result[correlation_cmd_result.index(':') + 1:].strip()
        raise NotImplementedError()

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
