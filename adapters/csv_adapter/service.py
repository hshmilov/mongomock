import re
import datetime
import logging
import urllib
import requests
import chardet
# pylint: disable=import-error
from smb.SMBHandler import SMBHandler

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import GetDevicesError
from axonius.clients.aws.utils import get_s3_object
from axonius.clients.csv.utils import get_column_types
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.clients.rest.consts import get_default_timeout
from axonius.fields import Field
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import make_dict_from_csv, normalize_var_name
from axonius.consts.csv_consts import get_csv_field_names

logger = logging.getLogger(f'axonius.{__name__}')

DEVICES_NEEDED_FIELDS = ['id', 'serial', 'mac_address', 'hostname', 'name']
USERS_NEEDED_FIELDS = ['id', 'username', 'mail', 'name']
SW_NEEDED_FIELDS = ['hostname', 'installed_sw_name']


# pylint: disable=R1702,R0201,R0912,R0915,R0914
class CsvAdapter(AdapterBase):
    DEFAULT_LAST_FETCHED_THRESHOLD_HOURS = 24

    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        file_name = Field(str, 'CSV File Name')
        etc_version = Field(str, 'Etcissue Version')

    class MyUserAdapter(UserAdapter):
        file_name = Field(str, 'CSV File Name')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        if not client_config.get('csv_http') and 'csv' not in client_config and not client_config.get('csv_share') \
                and not client_config.get('s3_bucket'):
            raise ClientConnectionException('Bad params. No File / URL / Share / Amazon S3 Bucket for CSV')
        self.create_csv_info_from_client_config(client_config)
        return client_config

    def create_csv_info_from_client_config(self, client_config):
        csv_data_bytes = None
        if client_config.get('csv_http'):
            try:
                csv_data_bytes = requests.get(client_config.get('csv_http'),
                                              verify=False,
                                              timeout=get_default_timeout()).content
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
        elif client_config.get('s3_bucket') or client_config.get('s3_object_location'):
            s3_bucket = client_config.get('s3_bucket')
            s3_object_location = client_config.get('s3_object_location')
            s3_access_key_id = client_config.get('s3_access_key_id')
            s3_secret_access_key = client_config.get('s3_secret_access_key')

            if not (s3_bucket and s3_object_location):
                raise ClientConnectionException(
                    f'Error - Please specify both Amazon S3 Bucket and Amazon S3 Object Location')

            if (s3_access_key_id or s3_secret_access_key) and not (s3_access_key_id and s3_secret_access_key):
                raise ClientConnectionException(f'Error - Please specify both access key id and secret access key, '
                                                f'or leave blank to use the attached IAM role')

            try:
                csv_data_bytes = get_s3_object(
                    bucket_name=s3_bucket,
                    object_location=s3_object_location,
                    access_key_id=s3_access_key_id,
                    secret_access_key=s3_secret_access_key
                )
            except Exception as e:
                if 'SignatureDoesNotMatch' in str(e):
                    raise ClientConnectionException(f'Amazon S3 Bucket - Invalid Credentials. Response is: {str(e)}')
                raise
        elif 'csv' in client_config:
            csv_data_bytes = self._grab_file_contents(client_config['csv'])

        if csv_data_bytes is None:
            raise Exception('Bad CSV, could not parse the data')
        encoding = chardet.detect(csv_data_bytes)['encoding']  # detect decoding automatically
        encoding = encoding or 'utf-8'
        csv_data = csv_data_bytes.decode(encoding)
        csv_dict = make_dict_from_csv(csv_data)
        fields = get_csv_field_names(csv_dict.fieldnames)
        is_users_csv = client_config.get('is_users_csv', False)
        is_installed_sw = client_config.get('is_installed_sw', False)
        if is_users_csv:
            csv_needed_fields = USERS_NEEDED_FIELDS
        elif is_installed_sw:
            csv_needed_fields = SW_NEEDED_FIELDS
            for id_field in csv_needed_fields:
                if id_field not in fields:
                    logger.error(f'Bad fields names {str(csv_dict.fieldnames)}')
                    raise Exception(f'Missing Software Fields')
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
        is_installed_sw = client_data.get('is_installed_sw', False)
        if is_users_csv:
            return None
        return self.create_csv_info_from_client_config(client_data), is_installed_sw

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'is_users_csv',
                    'title': 'Is Users CSV File',
                    'type': 'bool'
                },
                {
                    'name': 'is_installed_sw',
                    'title': 'Is Installed Software File',
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
                {
                    'name': 's3_bucket',
                    'title': 'Amazon S3 Bucket Name',
                    'type': 'string',
                },
                {
                    'name': 's3_object_location',
                    'title': 'Amazon S3 Object Location (Key)',
                    'type': 'string',
                },
                {
                    'name': 's3_access_key_id',
                    'title': 'Amazon S3 Access Key Id',
                    'description': 'Leave blank to use the attached IAM role',
                    'type': 'string',
                },
                {
                    'name': 's3_secret_access_key',
                    'title': 'Amazon S3 Secret Access Key',
                    'description': 'Leave blank to use the attached IAM role',
                    'type': 'string',
                    'format': 'password'
                }
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

        column_types = dict()
        try:
            if should_parse_all_columns:
                csv_data = list(csv_data)  # csv_data is a generator, we must get all values
                column_types = get_column_types(csv_data)
        except Exception:
            logger.exception(f'Could not parse column types')
        for user_raw in csv_data:
            try:
                user_obj = self._new_user_adapter()
                user_obj.file_name = file_name
                vals = {field_name: user_raw.get(fields[field_name][0]) for field_name in fields}

                user_id = str(vals.get('id', '') or vals.get('username') or vals.get('mail') or vals.get('name'))
                if not user_id:
                    logger.error(f'no user id for {user_raw}, continuing')
                    continue

                user_obj.id = file_name + '_' + user_id
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
                            field_type = column_types.get(column_name) or str
                            if not user_obj.does_field_exist(normalized_column_name):
                                # Currently we treat all columns as str
                                cn_capitalized = ' '.join([word.capitalize() for word in column_name.split(' ')])
                                user_obj.declare_new_field(
                                    normalized_column_name, Field(field_type, f'CSV {cn_capitalized}'))

                            if field_type == datetime.datetime:
                                value = parse_date(column_value)
                            elif field_type == float:
                                value = float(column_value)
                            elif field_type == int:
                                value = int(column_value)
                            else:
                                value = str(column_value)
                            user_obj[normalized_column_name] = value
                        except Exception:
                            logger.exception(f'Could not parse column {column_name} with value {column_value}')
                yield user_obj
            except Exception:
                logger.exception(f'Problem adding user: {str(user_raw)}')

    def _parse_instaleld_sw_file(self, csv_data, file_name):
        hostname_sw_dict = dict()
        fields = get_csv_field_names(csv_data.fieldnames)
        for device_raw in csv_data:
            try:
                vals = {field_name: device_raw.get(fields[field_name][0]) for field_name in fields}
                hostname = vals.get('hostname')
                if hostname not in hostname_sw_dict:
                    hostname_sw_dict[hostname] = []
                installed_sw_name = vals.get('installed_sw_name')
                installed_sw_version = vals.get('installed_sw_version')
                installed_sw_vendor = vals.get('installed_sw_vendor')
                sw_data = (installed_sw_name, installed_sw_version, installed_sw_vendor)
                hostname_sw_dict[hostname].append(sw_data)
            except Exception:
                logger.exception(f'Problem with device raw {device_raw}')
        for hostname, sw_list in hostname_sw_dict.items():
            try:
                device = self._new_device_adapter()
                device.file_name = file_name
                for sw_data in sw_list:
                    installed_sw_name, installed_sw_version, installed_sw_vendor = sw_data
                    device.add_installed_software(name=installed_sw_name,
                                                  version=installed_sw_version,
                                                  vendor=installed_sw_vendor)
                device.hostname = hostname
                device.id = file_name + '_' + hostname
                device.set_raw({})
                yield device
            except Exception:
                logger.exception(f'Problem with hostanme {hostname}')

    def _parse_raw_data(self, devices_raw_data):
        if devices_raw_data is None:
            return
        devices_raw_data_inner, is_installed_sw = devices_raw_data
        csv_data, should_parse_all_columns, file_name = devices_raw_data_inner
        if is_installed_sw:
            yield from self._parse_instaleld_sw_file(csv_data, file_name)
            return
        fields = get_csv_field_names(csv_data.fieldnames)
        if not any(id_field in fields for id_field in DEVICES_NEEDED_FIELDS):
            logger.error(f'Bad devices fields names {str(csv_data.fieldnames)}')
            raise GetDevicesError(f'Strong identifier is missing for devices')

        column_types = dict()
        try:
            if should_parse_all_columns:
                csv_data = list(csv_data)   # csv_data is a generator, we must get all values
                column_types = get_column_types(csv_data)
        except Exception:
            logger.exception(f'Could not parse column types')
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
                    logger.warning(f'can not get device id for {device_raw}, continuing')
                    continue

                device.id = file_name + '_' + device_id
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
                    pass

                ips = (vals.get('ip') or '').split(',')
                ips = [ip.strip() for ip in ips if ip.strip()]

                if vals.get('username'):
                    device.last_used_users = [vals.get('username')]

                device.add_ips_and_macs(macs, ips)

                try:
                    packages = vals.get('packages')
                    if packages and isinstance(packages, str):
                        packages = packages.split(' ')
                        for package in packages:
                            if len(package) < 100:
                                device.add_installed_software(name=package)
                except Exception:
                    logger.exception(f'Problem with packages')

                # pylint: disable=anomalous-backslash-in-string
                try:
                    nics_raw = vals.get('networkinterfaces')
                    if not isinstance(nics_raw, str):
                        nics_raw = ''
                    macs_nics = re.findall('ether ([^\s]+)', nics_raw)
                    macs_nics.extend(re.findall('HWaddr ([^\s]+)', nics_raw))
                    ips_nics = re.findall('inet ([^\s]+)', nics_raw)
                    ips_nics = [x.strip('addr:') for x in ips_nics]
                    device.add_ips_and_macs(macs=macs_nics, ips=ips_nics)
                except Exception:
                    logger.exception(f'Problem with nics')

                try:
                    etc_str = vals.get('etcissue')
                    if etc_str and ' ' in etc_str:
                        device.etc_version = etc_str.split(' ')[1]
                except Exception:
                    logger.exception(f'Problem with etcissue')

                device.set_raw(device_raw)

                if should_parse_all_columns:
                    for column_name, column_value in device_raw.items():
                        try:
                            normalized_column_name = 'csv_' + normalize_var_name(column_name)
                            field_type = column_types.get(column_name) or str
                            if not device.does_field_exist(normalized_column_name):
                                # Currently we treat all columns as str
                                cn_capitalized = ' '.join([word.capitalize() for word in column_name.split(' ')])
                                device.declare_new_field(
                                    normalized_column_name, Field(field_type, f'CSV {cn_capitalized}'))

                            if field_type == datetime.datetime:
                                value = parse_date(column_value)
                            elif field_type == float:
                                value = float(column_value)
                            elif field_type == int:
                                value = int(column_value)
                            else:
                                value = str(column_value)
                            device[normalized_column_name] = value
                        except Exception:
                            logger.warning(f'Could not parse column {column_name} with value {column_value}',
                                           exc_info=True)
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
