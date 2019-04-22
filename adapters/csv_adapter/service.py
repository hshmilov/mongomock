import datetime
import logging
import urllib
import requests
import chardet
from smb.SMBHandler import SMBHandler

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import GetDevicesError
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.clients.rest.consts import DEFAULT_TIMEOUT
from axonius.fields import Field
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import make_dict_from_csv, normalize_var_name
from axonius.consts.csv_consts import get_csv_field_names

logger = logging.getLogger(f'axonius.{__name__}')

DEVICES_NEEDED_FIELDS = ['id', 'serial', 'mac_address', 'hostname', 'name']
USERS_NEEDED_FIELDS = ['id', 'username', 'mail', 'name']


# pylint: disable=R1702,R0201,R0912,R0915,R0914
class CsvAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        file_name = Field(str, 'CSV File Name')

    class MyUserAdapter(UserAdapter):
        file_name = Field(str, 'CSV File Name')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        if not client_config.get('csv_http') and 'csv' not in client_config and not client_config.get('csv_share'):
            raise ClientConnectionException('Bad params. No File or URL or Share for CSV')
        self.create_csv_info_from_client_config(client_config)
        return client_config

    def create_csv_info_from_client_config(self, client_config):
        csv_data_bytes = None
        if client_config.get('csv_http'):
            try:
                csv_data_bytes = requests.get(client_config.get('csv_http'),
                                              verify=False,
                                              timeout=DEFAULT_TIMEOUT).content
            except Exception:
                logger.exception(f'Couldn\'t get csv info from URL')
        elif client_config.get('csv_share'):
            try:
                share_username = client_config.get('csv_share_username')
                share_password = client_config.get('csv_share_password')
                if not share_password or not share_username:
                    share_password = None
                    share_username = None
                share_path = client_config.get('csv_share')
                if not share_path.startswith('\\\\'):
                    raise Exception('Bad Share Format')
                share_path = share_path[2:]
                share_path = share_path.replace('\\', '/')
                if share_username and share_password:
                    share_path = f'{urllib.parse.quote(share_username)}:' \
                                 f'{urllib.parse.quote(share_password)}@{share_path}'
                share_path = 'smb://' + share_path
                opener = urllib.request.build_opener(SMBHandler)
                with opener.open(share_path) as fh:
                    csv_data_bytes = fh.read()
            except Exception:
                logger.exception(f'Couldn\'t get csv info from share')
        elif 'csv' in client_config:
            csv_data_bytes = self._grab_file_contents(client_config['csv'])
        if csv_data_bytes is None:
            raise Exception('Bad CSV, could not parse the data')
        encoding = chardet.detect(csv_data_bytes)['encoding']  # detect decoding automatically
        csv_data = csv_data_bytes.decode(encoding)
        csv_dict = make_dict_from_csv(csv_data)
        fields = get_csv_field_names(csv_dict.fieldnames)
        is_users_csv = client_config.get('is_users_csv', False)
        if is_users_csv:
            csv_needed_fields = USERS_NEEDED_FIELDS
        else:
            csv_needed_fields = DEVICES_NEEDED_FIELDS
        if not any(id_field in fields for id_field in csv_needed_fields):
            logger.error(f'Bad fields names {str(csv_dict.fieldnames)}')
            raise Exception(f'Strong identifier is missing')
        return csv_dict, True, client_config.get('user_id')

    def _query_users_by_client(self, key, data):
        is_users_csv = data.get('is_users_csv', False)
        if not is_users_csv:
            return None
        return self.create_csv_info_from_client_config(data)

    def _query_devices_by_client(self, client_name, client_data):
        is_users_csv = client_data.get('is_users_csv', False)
        if is_users_csv:
            return None
        return self.create_csv_info_from_client_config(client_data)

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
                    'title': 'CSV File Name',
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
                },
                {
                    'name': 'csv_share',
                    'title': 'CSV Share Path',
                    'type': 'string'
                },
                {
                    'name': 'csv_share_username',
                    'title': 'CSV Share Username',
                    'type': 'string'
                },
                {
                    'name': 'csv_share_password',
                    'title': 'CSV Share Password',
                    'type': 'string',
                    'format': 'password'
                },
            ],
            'required': [
                'user_id',
            ],
            'type': 'array'
        }

    def _parse_users_raw_data(self, user):
        if user is None:
            return

        csv_data, should_parse_all_columns, file_name = user
        fields = get_csv_field_names(csv_data.fieldnames)
        if not any(id_field in fields for id_field in USERS_NEEDED_FIELDS):
            logger.error(f'Bad user fields names {str(csv_data.fieldnames)}')
            raise GetDevicesError(f'Strong user identifier is missing for users')

        for user_raw in csv_data:
            try:
                user_obj = self._new_user_adapter()
                user_obj.file_name = file_name
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
        csv_data, should_parse_all_columns, file_name = devices_raw_data
        fields = get_csv_field_names(csv_data.fieldnames)
        if not any(id_field in fields for id_field in DEVICES_NEEDED_FIELDS):
            logger.error(f'Bad devices fields names {str(csv_data.fieldnames)}')
            raise GetDevicesError(f'Strong identifier is missing for devices')

        for device_raw in csv_data:
            try:
                device = self._new_device_adapter()
                device.file_name = file_name
                vals = {field_name: device_raw.get(fields[field_name][0]) for field_name in fields}

                macs = (vals.get('mac_address') or '').split(',')
                macs = [mac.strip() for mac in macs if mac.strip()]
                mac_as_id = macs[0] if macs else None

                device_id = str(vals.get('id', '')) or vals.get('serial') or mac_as_id or vals.get('hostname')
                if not device_id:
                    logger.error(f'can not get device id for {device_raw}, continuing')
                    continue

                device.id = device_id
                device.device_serial = vals.get('serial')
                device.name = vals.get('name')
                hostname = vals.get('hostname')
                if hostname == 'unknown':
                    hostname = None
                hostname_domain = None
                if hostname and '\\' in hostname:
                    hostname = hostname.split('\\')[1]
                    hostname_domain = hostname.split('\\')[0]
                device.hostname = hostname
                if not hostname:
                    device.hostname = vals.get('name')
                device.device_model = vals.get('model')
                device.domain = vals.get('domain') or hostname_domain
                try:
                    last_seen = parse_date(vals.get('last_seen'))
                    if last_seen:
                        device.last_seen = last_seen
                    else:
                        device.last_seen = datetime.datetime.fromtimestamp(int(vals.get('last_seen')))
                except Exception:
                    logger.debug(f'Problem adding last seen')

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

                if vals.get('username'):
                    device.last_used_users = [vals.get('username')]

                device.add_ips_and_macs(macs, ips)
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
