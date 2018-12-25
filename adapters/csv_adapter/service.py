import logging
import requests

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import GetDevicesError
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.clients.rest.consts import DEFAULT_TIMEOUT
from axonius.fields import Field
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import make_dict_from_csv, normalize_var_name
from csv_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=R1702,R0201,R0912,R0915,R0914
class CsvAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    class MyUserAdapter(UserAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        if not client_config.get('csv_http') and 'csv' not in client_config:
            raise ClientConnectionException('Bad params. No File or URL for CSV')
        if client_config.get('csv_http'):
            r = requests.get(client_config.get('csv_http'),
                             verify=False,
                             timeout=DEFAULT_TIMEOUT).content
            r.raise_for_status()
        return client_config

    def _query_users_by_client(self, key, data):
        is_users_csv = data.get('is_users_csv', False)
        if not is_users_csv:
            return None
        csv_data = None
        if data.get('csv_http'):
            try:
                csv_data = requests.get(data.get('csv_http'),
                                        verify=False,
                                        timeout=DEFAULT_TIMEOUT).content
            except Exception:
                logger.exception(f'Couldn\'t get csv info from URL')
        if 'csv' in data and csv_data is None:
            csv_data = self._grab_file_contents(data['csv']).decode('utf-8')
        return make_dict_from_csv(csv_data), True

    def _query_devices_by_client(self, client_name, client_data):
        is_users_csv = client_data.get('is_users_csv', False)
        if is_users_csv:
            return None
        csv_data = None
        if client_data.get('csv_http'):
            try:
                csv_data = requests.get(client_data.get('csv_http'),
                                        verify=False,
                                        timeout=DEFAULT_TIMEOUT).content
            except Exception:
                logger.exception(f'Couldn\'t get csv info from URL')

        if 'csv' in client_data and csv_data is None:
            csv_data = self._grab_file_contents(client_data['csv']).decode('utf-8')
        return make_dict_from_csv(csv_data), True

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
                    'name': 'csv_http',
                    'title': 'CSV URL Path',
                    'type': 'string'
                }
            ],
            'required': [
                'user_id',
            ],
            'type': 'array'
        }

    @staticmethod
    def get_csv_field_names(fieldnames):
        """
        iterates over a list of identifiers we defined and tries to see if there are some generic columns in the csv.
        :param fieldnames: list of str with field names
        :return: a dict in which the key is what we search for and the value is the list of column names in the csv
        """

        # transform all fields according to our rules
        fieldnames = {f.lower().replace('_', '').replace('-', '').replace(' ', ''): f for f in fieldnames}

        def search_for_fieldname(list_of_fields_to_search):
            found_fields = []
            for field in list_of_fields_to_search:
                if fieldnames.get(field):
                    found_fields.append(fieldnames.get(field))

            return found_fields

        final_dict = dict()
        for key, value in consts.IDENTIFIERS.items():
            column_names = search_for_fieldname(value)
            if column_names:
                final_dict[key] = column_names

        return final_dict

    def _parse_users_raw_data(self, user):
        if user is None:
            return

        csv_data, should_parse_all_columns = user
        fields = self.get_csv_field_names(csv_data.fieldnames)

        if not any(id_field in fields for id_field in ['id', 'username', 'mail', 'name']):
            logger.error(f'Bad user fields names {str(csv_data.fieldnames)}')
            raise GetDevicesError(f'Strong user identifier is missing for users')

        for user_raw in csv_data:
            try:
                user_obj = self._new_user_adapter()
                vals = {field_name: user_raw.get(fields[field_name][0]) for field_name in fields}

                user_id = str(vals.get('id', '') or vals.get('username') or vals.get('mail') or vals.get('name'))
                if not user_id:
                    logger.error(f'no user id for {user_raw}, continuing')
                    continue

                user_obj.id = user_id
                user_obj.username = vals.get('username')
                user_obj.first_name = vals.get('first_name')
                user_obj.last_name = vals.get('last_name')
                user_obj.mail = vals.get('mail')
                user_obj.display_name = vals.get('name')
                user_obj.domain = vals.get('domain')
                user_obj.set_raw(user_raw)

                if should_parse_all_columns:
                    for column_name, column_value in user_raw.items():
                        try:
                            if not column_name or not column_value:
                                logger.debug(f'Bad CSV fields. Name: {column_name} Value: {column_value}')
                                continue
                            normalized_column_name = 'csv_' + normalize_var_name(column_name)
                            if not user_obj.does_field_exist(normalized_column_name):
                                # Currently we treat all columns as str
                                cn_capitalized = ' '.join([word.capitalize() for word in column_name.split(' ')])
                                user_obj.declare_new_field(normalized_column_name, Field(str, f'CSV {cn_capitalized}'))

                            user_obj[normalized_column_name] = column_value
                        except Exception:
                            logger.exception(f'Could not parse column {column_name} with value {column_value}')
                yield user_obj
            except Exception:
                logger.exception(f'Problem adding user: {str(user_raw)}')

    def _parse_raw_data(self, devices_raw_data):
        if devices_raw_data is None:
            return
        csv_data, should_parse_all_columns = devices_raw_data
        fields = self.get_csv_field_names(csv_data.fieldnames)

        if not any(id_field in fields for id_field in ['id', 'serial', 'mac_address']):
            logger.error(f'Bad devices fields names {str(csv_data.fieldnames)}')
            raise GetDevicesError(f'Strong identifier is missing for devices')

        for device_raw in csv_data:
            try:
                device = self._new_device_adapter()
                vals = {field_name: device_raw.get(fields[field_name][0]) for field_name in fields}

                macs = (vals.get('mac_address') or '').split(',')
                macs = [mac.strip() for mac in macs if mac.strip()]
                mac_as_id = macs[0] if macs else None

                device_id = str(vals.get('id', '')) or vals.get('serial') or mac_as_id
                if not device_id:
                    logger.error(f'can not get device id for {device_raw}, continuing')
                    continue

                device.id = device_id
                device.device_serial = vals.get('serial')
                device.name = vals.get('name')
                device.hostname = vals.get('hostname')
                device.device_model = vals.get('model')
                device.domain = vals.get('domain')
                device.last_seen = vals.get('last_seen')
                device.device_manufacturer = vals.get('manufacturer')
                device.total_physical_memory = vals.get('total_physical_memory_gb')

                # OS is a special case, instead of getting the first found column we take all of them and combine them
                if 'os' in fields:
                    os_raw = '_'.join([device_raw.get(os_column) for os_column in fields['os']])
                    try:
                        device.figure_os(os_raw)
                    except Exception:
                        logger.error(f'Can not parse os {os_raw}')

                try:
                    device.os.kernel_version = vals.get('kernel')
                except Exception:
                    # os is probably not set
                    device.figure_os('')
                    device.os.kernel_version = vals.get('kernel')

                try:
                    cpu_speed = vals.get('cpu_speed')
                    architecture = vals.get('architecture')
                    if cpu_speed or architecture:
                        device.add_cpu(ghz=cpu_speed / (1024 ** 3), architecture=architecture)
                except Exception:
                    logger.exception(f'Problem setting cpu')

                ips = (vals.get('ip') or '').split(',')
                ips = [ip.strip() for ip in ips if ip.strip()]

                try:
                    if macs or ips:
                        for mac in (macs or [None]):
                            device.add_nic(mac=mac, ips=ips)
                except Exception:
                    logger.exception(f'Problem adding network interfaces {macs}, {ips}')

                device.set_raw(device_raw)

                if should_parse_all_columns:
                    for column_name, column_value in device_raw.items():
                        try:
                            normalized_column_name = 'csv_' + normalize_var_name(column_name)
                            if not device.does_field_exist(normalized_column_name):
                                # Currently we treat all columns as str
                                cn_capitalized = ' '.join([word.capitalize() for word in column_name.split(' ')])
                                device.declare_new_field(normalized_column_name, Field(str, f'CSV {cn_capitalized}'))

                            device[normalized_column_name] = column_value
                        except Exception:
                            logger.exception(f'Could not parse column {column_name} with value {column_value}')
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
