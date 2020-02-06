import datetime
import logging
import re

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import GetDevicesError
from axonius.consts import remote_file_consts
from axonius.consts.csv_consts import get_csv_field_names
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.dynamic_fields import put_dynamic_field
from axonius.utils.files import get_local_config_file
from axonius.utils.json import from_json
from axonius.utils.parsing import normalize_var_name
from axonius.utils.remote_file_utils import load_remote_data, test_file_reachability
from json_adapter.client_id import get_client_id
from json_adapter.consts import INSTALLED_SW_IDENTIFIERS

logger = logging.getLogger(f'axonius.{__name__}')

DEVICES_NEEDED_FIELDS = ['id', 'serial', 'mac_address', 'hostname', 'name']
USERS_NEEDED_FIELDS = ['id', 'username', 'mail', 'name']

# pylint: disable=R1702,R0201,R0912,R0915,R0914


class JsonAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        file_name = Field(str, 'JSON File Name')

    class MyUserAdapter(UserAdapter):
        file_name = Field(str, 'JSON File Name')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return test_file_reachability(client_config)

    def _connect_client(self, client_config):
        # test if loading data is possible. This also tests configuration.
        load_remote_data(client_config)
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific resource

        :param str client_name: The name of the resource
        :param obj client_data: Configuration required to fetch the resource

        :return: A json with all the attributes fetched from the resource
        """
        if not client_data.get('is_users', False):
            yield from self._query_entities_by_client(client_data)

    def _query_users_by_client(self, key, data):
        """

        Get all users from a specific resource
        :param str key: The name of the resource
        :param obj data: Configuration required to fetch the resource

        :return: A json with all the attributes fetched from the resource
        """
        if data.get('is_users', False):
            yield from self._query_entities_by_client(data)

    @staticmethod
    def _clients_schema():
        """
        The schema JsonAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'is_users',
                    'title': 'File contains users information',
                    'type': 'bool'
                },
                *remote_file_consts.FILE_CLIENTS_SCHEMA
            ],
            'required': [
                'is_users',
                *remote_file_consts.FILE_SCHEMA_REQUIRED
            ],
            'type': 'array'
        }

    def _query_entities_by_client(self, client_config):
        file_name, decoded_data = load_remote_data(client_config)
        json_data = from_json(decoded_data)
        if isinstance(json_data, list):
            for json_dict in json_data:
                try:
                    yield self._prepare_entity_dict(json_dict, client_config), file_name
                except Exception:
                    logger.exception(f'Failed to parse json entity: {json_dict}')
                    continue
        else:
            try:
                yield self._prepare_entity_dict(json_data, client_config), file_name
            except Exception:
                logger.exception(f'Failed to parse json entity: {json_data}')
                raise

    @staticmethod
    def _prepare_entity_dict(json_dict, client_config):
        fields = get_csv_field_names(json_dict.keys())
        is_users = client_config.get('is_users', False)
        if is_users:
            req_fields = USERS_NEEDED_FIELDS
        else:
            req_fields = DEVICES_NEEDED_FIELDS
        if not any(id_field in fields for id_field in req_fields):
            logger.error(f'Bad fields names {str(list(json_dict.keys()))}')
            raise Exception(f'Strong identifier is missing')
        return json_dict

    @staticmethod
    def _find_installed_sw_list(device_raw):
        for identifier in INSTALLED_SW_IDENTIFIERS:
            if identifier in device_raw:
                yield identifier

    @staticmethod
    def _parse_installed_sw(device, device_raw, fields):
        for field in fields['installed_sw_list']:
            try:
                if not isinstance(device_raw[field], list):
                    continue
                for sw_data in device_raw[field]:
                    if isinstance(sw_data, str):
                        device.add_installed_software(name=sw_data)
                        continue
                    try:
                        sw_fields = get_csv_field_names(sw_data)
                        vals = {field_name: sw_data.get(sw_fields[field_name][0])
                                for field_name in sw_fields}
                        installed_sw_name = vals.get('installed_sw_name')
                        installed_sw_version = vals.get('installed_sw_version')
                        installed_sw_vendor = vals.get('installed_sw_vendor')
                        device.add_installed_software(
                            name=installed_sw_name,
                            version=installed_sw_version,
                            vendor=installed_sw_vendor
                        )
                    except Exception as e:
                        logger.warning(f'Failed to parse sw data: {sw_data}. The error was: {str(e)}')
                        continue
            except Exception:
                logger.warning(f'Error parsing sw info from {device_raw[field]}')
                continue

    def _create_device(self, device_raw):
        device_raw, file_name = device_raw
        fields_raw = list(device_raw.keys())
        fields = get_csv_field_names(fields_raw)
        try:
            installed_sw_identifiers = list(self._find_installed_sw_list(device_raw))
        except Exception as e:
            logger.error(f'Failed to parse installed software for {device_raw}. '
                         f'The error was: {str(e)}')
            installed_sw_identifiers = None
        if installed_sw_identifiers:
            fields['installed_sw_list'] = installed_sw_identifiers
        try:
            gen_values = {field_name: device_raw.get(fields[field_name][0]) for field_name in fields}
            device = self._new_device_adapter()
            device.file_name = file_name

            # Figure out macs first as a backup id
            macs = (gen_values.get('mac_address') or '').split(',')
            macs = [mac.strip() for mac in macs if mac.strip()]
            mac_as_id = macs[0] if macs else None

            # Get an ID
            serial = gen_values.get('serial')
            hostname = gen_values.get('hostname')
            if hostname == 'unknown':
                hostname = None
            device_id = self._get_entity_id(device_raw, fields)
            device_id = device_id or serial or mac_as_id or hostname
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            device.id = f'{file_name}_{device_id}'

            # Handle Axonius Generic fields
            # duplicated from CSV adapter (with some modifications)
            device.device_serial = serial
            device.name = gen_values.get('name')
            device.device_model = gen_values.get('model')
            device.device_manufacturer = gen_values.get('manufacturer')
            device.total_physical_memory = gen_values.get('total_physical_memory_gb')

            self._parse_device_hostname(device, gen_values, hostname)

            try:
                last_seen = parse_date(gen_values.get('last_seen'))
                if last_seen:
                    device.last_seen = last_seen
                else:
                    device.last_seen = datetime.datetime.fromtimestamp(
                        int(gen_values.get('last_seen')))
            except Exception:
                logger.debug(f'Problem adding last seen')

            self._parse_device_os(device, device_raw, fields)

            try:
                device.os.kernel_version = gen_values.get('kernel')
            except Exception:
                pass

            ips = (gen_values.get('ip') or '').split(',')
            ips = [ip.strip() for ip in ips if ip.strip()]
            if gen_values.get('ip') == 'unknown':
                ips = []

            if gen_values.get('username'):
                device.last_used_users = [gen_values.get('username')]

            device.add_ips_and_macs(macs, ips)

            try:
                packages = gen_values.get('packages')
                if packages and isinstance(packages, str):
                    packages = packages.split(' ')
                if packages and isinstance(packages, list):
                    for package in packages:
                        if not isinstance(package, str):
                            continue
                        if len(package) < 100:
                            device.add_installed_software(name=package)
            except Exception:
                logger.exception(f'Problem with packages')

            self._parse_device_nics(device, gen_values)

            try:
                cve_ids = gen_values.get('cve_id')
                if isinstance(cve_ids, str) and cve_ids:
                    cve_ids = cve_ids.split(',')
                    for cve_id in cve_ids:
                        device.add_vulnerable_software(cve_id=cve_id)
            except Exception:
                logger.warning(f'Problem with cve id', exc_info=True)

            if 'installed_sw_list' in fields:
                self._parse_installed_sw(device, device_raw, fields)

            # And now the dynamic fields....
            try:
                self._parse_entity_dynamic(device, device_raw)
            except Exception:
                message = f'Failed to parse dynamic fields for {device_raw}'
                logger.warning(message)
                logger.debug(message, exc_info=True)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Json Device for {device_raw}')
            return None

    @staticmethod
    def _parse_device_os(device_obj, device_raw, fields):
        # OS is a special case, instead of getting the first found key we take all
        # of them and combine them!
        if 'os' in fields:
            os_raw = '_'.join([device_raw.get(os_column) for os_column in fields['os']])
            try:
                device_obj.figure_os(os_raw)
            except Exception:
                logger.error(f'Can not parse os {os_raw}')

    @staticmethod
    def _parse_device_hostname(device_obj, device_raw_norm, hostname):
        hostname_domain = None
        if hostname and '\\' in hostname:
            hostname = hostname.split('\\')[1]
            hostname_domain = hostname.split('\\')[0]
        device_obj.hostname = hostname
        if not hostname:
            device_obj.hostname = device_raw_norm.get('name')
        device_obj.domain = device_raw_norm.get('domain') or hostname_domain

    @staticmethod
    def _parse_device_nics(device_obj, device_raw_norm):
        # pylint: disable=anomalous-backslash-in-string
        try:
            nics_raw = device_raw_norm.get('networkinterfaces')
            if not isinstance(nics_raw, str):
                nics_raw = ''
            macs_nics = re.findall('ether ([^\s]+)', nics_raw)
            macs_nics.extend(re.findall('HWaddr ([^\s]+)', nics_raw))
            ips_nics = re.findall('inet ([^\s]+)', nics_raw)
            ips_nics = [x.strip('addr:') for x in ips_nics]
            device_obj.add_ips_and_macs(macs=macs_nics, ips=ips_nics)
        except Exception:
            logger.exception(f'Problem with nics')

    def _parse_raw_data(self, devices_raw_data):
        for device_raw_data in devices_raw_data:
            device_raw = device_raw_data
            device = self._create_device(device_raw)
            if device:
                yield device

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        for user_raw in users_raw_data:
            user_obj = self._create_user(user_raw)
            if user_obj:
                yield user_obj

    @staticmethod
    def _get_field_name(field_names, name):
        return field_names.get(name, [None, ])[0]

    @staticmethod
    def _get_raw(entity_raw, fields, field_name, d_value=None):
        field = JsonAdapter._get_field_name(fields, field_name)
        return entity_raw.get(field, d_value)

    @staticmethod
    def _get_entity_id(entity_raw, fields):
        id_fields = fields.get('id')
        if not id_fields:
            return None
        entity_id = None
        for id_field in id_fields:
            if entity_raw.get(id_field):
                entity_id = entity_raw.get(id_field)
                break
        return entity_id

    def _create_user(self, user_data):
        user_raw, file_name = user_data
        fields_raw = list(user_raw.keys())
        fields = get_csv_field_names(fields_raw)
        if not any(id_field in fields for id_field in USERS_NEEDED_FIELDS):
            logger.error(f'Bad user fields names {str(fields_raw)}')
            raise GetDevicesError(f'Strong user identifier is missing for users')
        try:
            user = self._new_user_adapter()
            user.file_name = file_name

            # Generic Axonius stuff
            entity_id = self._get_entity_id(user_raw, fields)
            if entity_id is None:
                logger.warning(f'No user id for {user_raw}.')
                return None
            user.id = f'{file_name}_{entity_id}'
            user.username = self._get_raw(user_raw, fields, 'username')
            user.first_name = self._get_raw(user_raw, fields, 'first_name')
            user.last_name = self._get_raw(user_raw, fields, 'last_name')
            user.mail = self._get_raw(user_raw, fields, 'mail')
            user.display_name = self._get_raw(user_raw, fields, 'name')
            user.domain = self._get_raw(user_raw, fields, 'domain')
            user.username = self._get_raw(user_raw, fields, 'username')
            # And now for something completely different...
            self._parse_entity_dynamic(user, user_raw)
            user.set_raw(user_raw)
            return user
        except Exception as e:
            message = f'Failed to parse user data for {user_raw}. The error was: {str(e)}'
            logger.warning(message)
            return None

    @staticmethod
    def _parse_entity_dynamic(entity_obj, entity_raw):
        for key, val in entity_raw.items():
            try:
                if not key or not val:
                    logger.debug(f'Bad item. Key "{key}" ; Value "{val}"')
                    continue
                normalized_var_name = normalize_var_name(key)
                field_title = ' '.join(
                    [word.capitalize() for word in key.split(' ')])
                if entity_obj.does_field_exist(normalized_var_name):
                    # Make sure not to overwrite existing data
                    normalized_var_name = 'json_' + normalized_var_name
                    field_title = f'JSON {field_title}'
                put_dynamic_field(entity_obj, normalized_var_name, val, field_title)
            except Exception as e:
                logger.warning(f'Failed to add {key}:{val} to entity {entity_obj.id}: '
                               f'Got {str(e)}')
                continue

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
