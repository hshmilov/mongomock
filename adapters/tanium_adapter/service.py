# pylint: disable=E0401
import datetime
import logging

import ipaddress

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, DeviceAdapterOS, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import normalize_var_name, format_ip
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field, ListField, JsonStringFormat
from tanium_adapter.connection import TaniumConnection
from tanium_adapter.consts import ENDPOINT_TYPE, DISCOVERY_TYPE, DISCOVER_METHODS, SQ_TYPE, ASSET_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


def check_user_name(user_name):
    check = format(user_name).lower()
    skips = ['uninitialized', 'waiting for login']
    if user_name and not any([x in check for x in skips]):
        return True
    return False


def calc_bytes_gb(num):
    if num is None:
        return None
    try:
        return num / (1024 ** 3)
    except Exception:
        logger.error(f'unable to convert bytes {num} to gb')
        return None


def calc_ms_days(num):
    if num is None:
        return None
    try:
        return num / 1000 / 60 / 60 / 24
    except Exception:
        logger.error(f'unable to convert ms {num} to days')
        return None


def calc_ghz(num):
    if num is None:
        return None
    try:
        return num / 1000 / 1000 / 1000
    except Exception:
        logger.error(f'unable to convert {num} to ghz')
        return None


# pylint: disable=too-many-branches
def map_tanium_sq_value_type(value, value_type: str):
    """Value type mappings from tanium.

    Value type maps:

    Version            str -> version (JsonStringFormat.version)
    BESDate            str -> datetime
    IPAddress          str -> ip address
    WMIDate            str -> datetime
    NumericInteger     str -> int
    Hash               str
    String             str
    Numeric            str (number-LIKE, not necessarily an integer)
    TimeDiff           str (numeric + "Y|MO|W|D|H|M|S" i.e. 2 years, 3 months, 18 days, 4 hours, 22 minutes)
    DataSize           str (numeric + B|K|M|G|T i.e. 125MB, 23K, 34.2Gig)
    VariousDate        str (?)
    RegexMatch         str (?)
    LastOperatorType   str (?)
    """
    def check_value(checkv):
        if checkv is None or checkv == '' or '[no results]' in checkv:
            return False
        return True

    if isinstance(value, (tuple, list)):
        value = [x for x in value if check_value(x)]
        if not value:
            return None, {}
    else:
        if not check_value(value):
            return None, {}

    field_args = {
        'field_type': str,
        'converter': None,
        'json_format': None,
    }

    if value_type == 'NumericInteger':
        field_args['field_type'] = int
        if isinstance(value, (list, tuple)):
            if any(['.' in x for x in value]):
                field_args['field_type'] = float
                value = [float(x) for x in value]
            else:
                value = [int(x) for x in value]
        else:
            if '.' in value:
                field_args['field_type'] = float
                value = float(value)
            else:
                value = int(value)
    elif value_type == 'Version':
        field_args['json_format'] = JsonStringFormat.version
    elif value_type in ['BESDate', 'WMIDate']:
        if isinstance(value, (list, tuple)):
            value = [parse_date(x) for x in value]
        else:
            value = parse_date(value)
        field_args['field_type'] = datetime.datetime
    elif value_type == 'IPAddress' and ':' not in value:
        field_args['converter'] = format_ip
        field_args['json_format'] = JsonStringFormat.ip
    return value, field_args


# pylint: disable=R0912
def put_tanium_sq_dynamic_field(entity: SmartJsonClass, name: str, value_map: dict, is_sub_field: bool = False):
    value = value_map.get('value', None)
    value_type = value_map.get('type', None)

    # type is a string populated by connection.py, so it should never be empty
    # value should always be either a non-empty list of strings or a non-empty string
    if not value_type or not isinstance(value_type, (list, tuple, str)) or value in [[], None, '']:
        return

    if is_sub_field:
        key = normalize_var_name(name).lower()
        title = name
        field_type = Field
    else:
        key = normalize_var_name(f'sensor_{name}').lower()
        title = f'Sensor: {name}'
        field_type = ListField

    if value_type == 'object':
        if not entity.does_field_exist(field_name=key):
            class SmartJsonClassInstance(SmartJsonClass):
                pass

            field_value = field_type(field_type=SmartJsonClassInstance, title=title)
            entity.declare_new_field(field_name=key, field_value=field_value)

        for item in value:
            # pylint: disable=W0212
            smartjsonclass_instance = entity.get_field_type(key)._type()

            for d_key, d_map in item.items():
                put_tanium_sq_dynamic_field(
                    entity=smartjsonclass_instance,
                    name=d_key,
                    value_map=d_map,
                    is_sub_field=True,
                )

            entity[key].append(smartjsonclass_instance)
    else:
        if not entity.does_field_exist(field_name=key):
            try:
                value, field_args = map_tanium_sq_value_type(value=value, value_type=value_type)
            except Exception:
                logger.exception(f'Failed to map value {value} with type {value_type}')
                return
            if value in [None, []]:
                return
            field_value = field_type(title=title, **field_args)
            entity.declare_new_field(field_name=key, field_value=field_value)

        if isinstance(value, (list, tuple)):
            for item in value:
                entity[key].append(item)
        else:
            entity[key] = value


class TaniumAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        tanium_type = Field(str, 'Tanium Device Type', enum=[ENDPOINT_TYPE, DISCOVERY_TYPE, SQ_TYPE, ASSET_TYPE])
        created_at = Field(datetime.datetime, 'Created At')
        updated_at = Field(datetime.datetime, 'Updated At')
        is_managed = Field(bool, 'Discover Is Managed')
        unmanageable = Field(bool, 'Discover Unmanageable')
        ignored = Field(bool, 'Discover Ignored')
        methods_used = ListField(str, 'Discover Methods Used')
        natipaddress = Field(str, 'Discover NAT IP Address')
        discovery_tags = ListField(str, 'Discover Tags')
        sensor_tags = ListField(str, 'Sensor Tags')
        chassis_type = Field(str, 'Chassis Type')
        sq_name = Field(str, 'Saved Question Name')
        sq_query_text = Field(str, 'Saved Question Query Text')
        sq_expiration = Field(datetime.datetime, 'Saved Question Expiration')
        sq_selects = ListField(str, 'Saved Question Selects')
        server_name = Field(str, 'Tanium Server')
        server_version = Field(str, 'Tanium Server Version', json_format=JsonStringFormat.version)
        asset_report = Field(str, 'Asset Report Name')
        asset_report_description = Field(str, 'Asset Report Description')
        asset_report_category = Field(str, 'Asset Report Category')
        asset_report_created_at = Field(datetime.datetime, 'Asset Report Created At')
        asset_report_updated_at = Field(datetime.datetime, 'Asset Report Updated At')
        module_version = Field(str, 'Module Version', json_format=JsonStringFormat.version)

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        # add all of the elements of the cnx to the client id to ensure uniqueness
        domain = client_config['domain']
        username = client_config['username']
        fetch_system_status = client_config.get('fetch_system_status', True)
        fetch_discovery = (client_config.get('fetch_discovery') or False)
        asset_dvc = client_config.get('asset_dvc')
        sq_name = client_config.get('sq_name')

        client_id = [
            f'{domain}',
            f'{username}',
            f'status-{fetch_system_status}',
            f'asset-{asset_dvc}',
            f'disco-{fetch_discovery}',
            f'sq-{sq_name}',
        ]
        return '_'.join(client_id)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = TaniumConnection(
            domain=client_config['domain'],
            verify_ssl=client_config['verify_ssl'],
            username=client_config['username'],
            password=client_config['password'],
            https_proxy=client_config.get('https_proxy'),
        )
        with connection:
            connection.advanced_connect(
                sq_name=client_config.get('sq_name'),
                fetch_system_status=client_config.get('fetch_system_status', True),
                fetch_discovery=(client_config.get('fetch_discovery') or False),
                asset_dvc=client_config.get('asset_dvc'),
            )
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config), client_config
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint: disable=R0201
    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Tanium domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Tanium connection

        :return: A json with all the attributes returned from the Tanium Server
        """
        connection, client_config = client_data
        fetch_discovery = (client_config.get('fetch_discovery') or False)
        fetch_system_status = client_config.get('fetch_system_status', True)
        asset_dvc = client_config.get('asset_dvc')
        sq_name = client_config.get('sq_name')
        sq_max_hours = (client_config.get('sq_max_hours') or 0)
        sq_refresh = (client_config.get('sq_refresh') or False)
        domain = client_config['domain']

        with connection:
            yield from connection.get_device_list(
                fetch_system_status=fetch_system_status,
                fetch_discovery=fetch_discovery,
                asset_dvc=asset_dvc,
                sq_name=sq_name,
                sq_max_hours=sq_max_hours,
                sq_refresh=sq_refresh,
                client_name=client_name,
                domain=domain,
            )

    @staticmethod
    def _clients_schema():
        """
        The schema TaniumAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Tanium Domain',
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
                    'name': 'fetch_system_status',
                    'type': 'bool',
                    'title': 'Fetch devices from Tanium System Status',
                },
                {
                    'name': 'fetch_discovery',
                    'type': 'bool',
                    'title': 'Fetch devices from Tanium Discover Module'
                },
                {
                    'name': 'asset_dvc',
                    'type': 'string',
                    'title': 'Tanium Asset Module Report Name'
                },
                {
                    'name': 'sq_name',
                    'type': 'string',
                    'title': 'Saved Question Names (comma seperated)'
                },
                {
                    'name': 'sq_refresh',
                    'title': 'Always re-ask Saved Question',
                    'type': 'bool'
                },
                {
                    'name': 'sq_max_hours',
                    'title': 'Re-ask Saved Question if results are older than N hours',
                    'type': 'integer'
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
                'sq_refresh',
                'verify_ssl',
                'fetch_discovery',
                'fetch_system_status',
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_endpoint_device(self, device_raw, metadata):
        try:
            device = self._new_device_adapter()
            device.server_name = metadata['server_name']
            device.server_version = metadata['server_version']
            device.tanium_type = ENDPOINT_TYPE
            device_id = device_raw.get('computer_id')
            if not device_id:
                logger.warning(f'Bad system status device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + device_raw.get('host_name')
            device.uuid = str(device_raw.get('computer_id')) if device_raw.get('computer_id') else None
            hostname = device_raw.get('host_name')
            if hostname and hostname.endswith('(none)'):
                hostname = hostname[:-len('(none)')]
            device.hostname = hostname
            device.add_agent_version(agent=AGENT_NAMES.tanium, version=device_raw.get('full_version'))
            device.last_seen = parse_date(device_raw.get('last_registration'))
            ip_address = device_raw.get('ipaddress_client')
            if ip_address:
                device.add_nic(None, ip_address.split(','))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching System Status Device {device_raw}')
            return None

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_discovery_device(self, device_raw, metadata):
        try:
            module_version = metadata.get('workbenches', {}).get('discover', {}).get('version')
        except Exception:
            logger.exception(f'Problem parsing discover module version from metadata {metadata}')
            module_version = None

        try:
            device = self._new_device_adapter()
            device.server_name = metadata['server_name']
            device.server_version = metadata['server_version']
            device.tanium_type = DISCOVERY_TYPE
            device.module_version = module_version
            is_managed = device_raw.get('ismanaged') == 1
            if not is_managed:
                device.adapter_properties = [AdapterProperty.Network]
            device_id = device_raw.get('macaddress')
            if not device_id:
                logger.warning(f'Bad discover module device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + str(device_raw.get('computerid'))
            # ips = [device_raw.get('ipaddress')] if device_raw.get('ipaddress') else None
            ips_raw = device_raw.get('ipaddress')
            if ips_raw in ['172.17.0.1', '172.18.0.1']:
                ips_raw = None
            ips = [ips_raw] if ips_raw else None
            device.add_nic(mac=device_raw.get('macaddress'), ips=ips)
            device.uuid = str(device_raw.get('computerid')) if device_raw.get('computerid') else None
            device.natipaddress = device_raw.get('natipaddress')
            device.hostname = device_raw.get('hostname')
            try:
                if isinstance(device_raw.get('tags'), str) and device_raw.get('tags'):
                    device.discovery_tags = device_raw.get('tags').split(',')
            except Exception:
                logger.exception(f'Problem getting tags for {device_raw}')
            try:
                if isinstance(device_raw.get('ports'), str) and device_raw.get('ports'):
                    for port_raw in device_raw.get('ports').split(','):
                        device.add_open_port(port_id=port_raw)
            except Exception:
                logger.exception(f'Problem getting ports for {device_raw}')
            device.figure_os(device_raw.get('os'))
            try:
                if isinstance(device_raw.get('method'), str) and device_raw.get('method'):
                    methods = device_raw.get('method').split(',')
                    methods_used = dict(zip(DISCOVER_METHODS, methods))
                    for key, value in methods_used.items():
                        if value == '1':
                            device.methods_used.append(key)
            except Exception:
                logger.exception(f'Problem getting methods for {device_raw}')

            updated_at = parse_date(device_raw.get('updatedAt'))
            created_at = parse_date(device_raw.get('createdAt'))
            discovered_at = parse_date(device_raw.get('lastDiscoveredAt'))

            device.updated_at = updated_at
            device.last_seen = discovered_at
            device.created_at = created_at
            device.first_seen = created_at

            if isinstance(device_raw.get('unmanageable'), int):
                device.unmanageable = device_raw.get('unmanageable') == 1
            if isinstance(device_raw.get('ismanaged'), int):
                device.is_managed = is_managed
            if isinstance(device_raw.get('ignored'), int):
                device.ignored = device_raw.get('ignored') == 1
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Discover Device {device_raw}')
            return None

    # pylint: disable=too-many-branches,too-many-locals
    def _create_asset_device(self, device_raw, metadata):
        try:
            module_version = metadata.get('workbenches', {}).get('asset', {}).get('version')
        except Exception:
            logger.exception(f'Problem parsing asset module version from metadata {metadata}')
            module_version = None

        try:
            device_raw, report_meta = device_raw
            report_info = report_meta.get('data', {}).get('report', {})
            device = self._new_device_adapter()

            computer_id = device_raw.get('computer_id')
            system_uuid = device_raw.get('system_uuid')

            if not computer_id and not system_uuid:
                logger.warning(f'Bad asset module device with no computer_id or system_uuid {device_raw}')
                return None

            if not computer_id:
                device.adapter_properties = [AdapterProperty.Network]

            report_name = report_info.get('reportName')

            use_id = computer_id or system_uuid
            device.id = f'ASSET_DEVICE_{report_name}_{use_id}'
            device.uuid = format(use_id)

            updated_at = parse_date(device_raw.get('updated_at'))
            created_at = parse_date(device_raw.get('created_at'))

            device.created_at = created_at
            device.first_seen = created_at
            device.updated_at = updated_at
            device.last_seen = updated_at

            device.module_version = module_version
            device.server_name = metadata.get('server_name')
            device.server_version = metadata.get('server_version')
            device.tanium_type = ASSET_TYPE
            device.asset_report = report_name
            device.asset_report_description = report_info.get('description')
            device.asset_report_category = report_info.get('categoryName')
            device.asset_report_created_at = parse_date(report_info.get('createdAt'))
            device.asset_report_updated_at = parse_date(report_info.get('updatedAt'))
            user_name = device_raw.get('user_name')
            if check_user_name(user_name):
                device.last_used_users.append(user_name)
            device.hostname = device_raw.get('computer_name')
            device.device_serial = device_raw.get('serial_number')
            device.figure_os(device_raw.get('operating_system') or device_raw.get('os_platform'))
            service_pack = device_raw.get('service_pack')
            if service_pack and 'no service pack found' not in format(service_pack).lower():
                device.os.sp = service_pack
            device.os.build = device_raw.get('os_version')
            device.device_manufacturer = device_raw.get('manufacturer')
            device.device_model = device_raw.get('model')
            device.domain = device_raw.get('domain_name')
            device.total_physical_memory = calc_bytes_gb(device_raw.get('ram'))
            device.uptime = calc_ms_days(device_raw.get('uptime'))
            device.add_cpu(
                name=device_raw.get('cpu_name'),
                cores=device_raw.get('cpu_core'),
                ghz=calc_ghz(device_raw.get('cpu_speed')),
                manufacturer=device_raw.get('cpu_manufacturer'),
            )
            adapters = device_raw.get('ci_network_adapter', []) or []
            for adapter in adapters:
                try:
                    subnet_mask = adapter.get('subnet_mask')
                    ipv4_address = adapter.get('ipv4_address')
                    try:
                        subnet_mask = [format(ipaddress.ip_network(subnet_mask))]
                    except Exception:
                        logger.exception(f'Problem parsing subnet {subnet_mask} for network adapter {adapter}')
                        subnet_mask = None

                    device.add_nic(
                        ips=[ipv4_address] if ipv4_address else None,
                        mac=adapter.get('mac_address'),
                        subnets=subnet_mask,
                        gateway=adapter.get('gateway'),
                        name=adapter.get('name'),

                    )
                except Exception:
                    logger.exception(f'Problem parsing network adapter {adapter}')

            ip_address = device_raw.get('ip_address')
            if not adapters and ip_address:
                device.add_nic(ips=[ip_address])

            apps_raw = device_raw.get('ci_installed_application', []) or []
            for app_raw in apps_raw:
                try:
                    device.add_installed_software(
                        name=app_raw.get('normalized_name') or app_raw.get('name'),
                        version=app_raw.get('version'),
                        vendor=app_raw.get('normalized_vendor') or app_raw.get('vendor'),

                    )
                except Exception:
                    logger.exception(f'Problem parsing app {app_raw}')

            ms_apps_raw = device_raw.get('ci_windows_installer_application', []) or []
            for app_raw in ms_apps_raw:
                try:
                    device.add_installed_software(
                        name=app_raw.get('name'),
                        version=app_raw.get('version'),
                        vendor=app_raw.get('vendor'),
                    )
                except Exception:
                    logger.exception(f'Problem parsing ms app {app_raw}')

            disks = device_raw.get('ci_logical_disk', []) or []
            for disk in disks:
                try:
                    disk_device = disk.get('name')
                    disk_path = disk.get('mount_point')

                    skips = ['loop', 'tmp', 'overlay']
                    check = format(disk_device).lower()
                    if any([(x in check or x in disk_device) for x in skips]) or not disk_path:
                        continue

                    device.add_hd(
                        path=disk_path,
                        device=disk_device,
                        file_system=disk.get('file_system'),
                        total_size=calc_bytes_gb(disk.get('size')),
                        free_size=calc_bytes_gb(disk.get('free_space')),
                        description=disk.get('media_type'),
                    )
                except Exception:
                    logger.exception(f'Problem parsing disk {disk}')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Asset Device {device_raw}')
            return None

    @property
    def _values_skip(self):
        return ['n/a', '[no results]']

    @property
    def _values_empty(self):
        return [None, '', []]

    # pylint: disable=too-many-branches,too-many-locals
    def _create_sq_device(self, device_raw, metadata):
        def _check_sensor_data(sensor_data, first=False):
            value = sensor_data.get('value', None)
            if value in self._values_empty or not isinstance(value, list):
                return None

            value_check = [format(x).lower() for x in value]

            if any([x in y for y in value_check for x in self._values_skip]):
                return None

            if first:
                if not value:
                    return None
                return value[0]
            return value

        try:
            device_raw, sq_name, question = device_raw
            device = self._new_device_adapter()
            device.server_name = metadata.get('server_name')
            device.server_version = metadata.get('server_version')
            device.tanium_type = SQ_TYPE
            device.sq_name = sq_name
            device.sq_query_text = question.get('query_text')
            device.sq_expiration = parse_date(question.get('expiration'))
            device.os = DeviceAdapterOS()

            try:
                device.sq_selects = [x.get('sensor', {}).get('name') for x in question.get('selects', [])]
            except Exception:
                logger.exception(f'Problem with parsing sensors from selects in question {question}')

            if 'Computer ID' not in device_raw:
                logger.warning(f'Bad saved question device with no id {device_raw}')
                return None
            for sensor_name, sensor_data in device_raw.items():
                try:
                    if sensor_name == 'Computer ID':
                        computer_id = _check_sensor_data(sensor_data, True)
                        if not computer_id:
                            logger.warning(f'Bad device with no id {device_raw}')
                            return None
                        computer_id = str(computer_id)
                        device.id = f'SQ_DEVICE_{sq_name}_{computer_id}'
                        device.uuid = computer_id
                    elif sensor_name == 'Computer Name':
                        device.hostname = _check_sensor_data(sensor_data, True)
                    elif sensor_name == 'Computer Serial Number':
                        device.device_serial = _check_sensor_data(sensor_data, True)
                    elif sensor_name in ['IP Address', 'IPv4 Address', 'IPv6 Address', 'Static IP Addresses']:
                        device.add_nic(ips=_check_sensor_data(sensor_data, False))
                    elif sensor_name == 'Installed Applications':
                        apps_raw = _check_sensor_data(sensor_data, False) or []
                        for app_raw in apps_raw:
                            try:
                                app_name = (app_raw.get('Name') or {}).get('value')
                                app_version = (app_raw.get('Version') or {}).get('value')
                                app_version = None if 'n/a' in format(app_version).lower() else app_version
                                device.add_installed_software(name=app_name,
                                                              version=app_version)
                            except Exception:
                                logger.exception(f'Problem with app raw {app_raw}')
                    elif sensor_name == 'Chassis Type':
                        device.chassis_type = _check_sensor_data(sensor_data, True)
                    elif sensor_name == 'Last Logged In User':
                        users = _check_sensor_data(sensor_data, False) or []
                        users = [x for x in users if check_user_name(x)]
                        device.last_used_users.extend(users)
                    elif sensor_name == 'Last Reboot':
                        device.set_boot_time(boot_time=parse_date(_check_sensor_data(sensor_data, True)))
                    elif sensor_name == 'Model':
                        device.device_model = _check_sensor_data(sensor_data, True)
                    elif sensor_name == 'Manufacturer':
                        device.device_manufacturer = _check_sensor_data(sensor_data, True)
                    elif sensor_name == 'Custom Tags':
                        if _check_sensor_data(sensor_data, True) \
                                and _check_sensor_data(sensor_data, True) != '[No Tags]':
                            device.sensor_tags = _check_sensor_data(sensor_data, False)
                    elif sensor_name == 'Open Ports':
                        for port_raw in _check_sensor_data(sensor_data, False):
                            device.add_open_port(port_id=port_raw)
                    elif sensor_name == 'CPU Details':
                        cpu_data = _check_sensor_data(sensor_data, True)
                        if not isinstance(cpu_data, dict):
                            cpu_data = {}
                        device.add_cpu(name=(cpu_data.get('CPU') or {}).get('value'),
                                       cores=int((cpu_data.get('Total Cores') or {}).get('value')))
                    elif sensor_name == 'Network Adapters':
                        nics_raw = _check_sensor_data(sensor_data, False)
                        for nic_raw in nics_raw:
                            try:
                                ips = (nic_raw.get('IP Address') or {}).get('value')
                                if ips:
                                    ips = [ips]
                                else:
                                    ips = None
                                mac = (nic_raw.get('MAC Address') or {}).get('value')
                                device.add_nic(mac=mac, ips=ips)
                            except Exception:
                                logger.exception(f'Problem with nic {nic_raw}')
                    elif sensor_name == 'Operating System':
                        device.figure_os(_check_sensor_data(sensor_data, True))
                    elif sensor_name == 'Service Details':
                        for service_raw in _check_sensor_data(sensor_data, False) or []:
                            display_name = (service_raw.get('Service Display Name') or {}).get('value')
                            service_status = (service_raw.get('Service Status') or {}).get('value')
                            service_name = (service_raw.get('Service Name') or {}).get('value')
                            device.add_service(display_name=display_name,
                                               name=service_status,
                                               status=service_name)
                    elif sensor_name == 'Service Pack':
                        service_pack = _check_sensor_data(sensor_data, True)
                        if service_pack and 'no service pack found' not in format(service_pack).lower():
                            device.os.sp = service_pack
                    elif sensor_name in ['RAM', 'Total Memory']:
                        try:
                            total_memory = format(_check_sensor_data(sensor_data, True)).lower().replace(' mb', '')
                            device.total_physical_memory = int(total_memory) / 1024
                        except Exception:
                            logger.exception(f'Problem parsing total memory from {sensor_name}: {sensor_data}')
                    elif sensor_name == 'Uptime':
                        try:
                            device.uptime = int(_check_sensor_data(sensor_data, True).lower().replace(' days', ''))
                        except Exception:
                            logger.exception(f'Problem parsing uptime from {sensor_name}: {sensor_data}')
                except Exception:
                    logger.exception(f'Problem with sensor name {sensor_name}')

                try:
                    put_tanium_sq_dynamic_field(
                        entity=device,
                        name=sensor_name,
                        value_map=sensor_data,
                        is_sub_field=False,
                    )
                except Exception:
                    logger.exception(f'Failed putting key {sensor_name!r} with value {sensor_data!r}')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Saved Question Device {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, metadata, device_type in devices_raw_data:
            device = None
            if device_type == ENDPOINT_TYPE:
                device = self._create_endpoint_device(device_raw=device_raw, metadata=metadata)
            elif device_type == DISCOVERY_TYPE:
                device = self._create_discovery_device(device_raw=device_raw, metadata=metadata)
            elif device_type == SQ_TYPE:
                device = self._create_sq_device(device_raw=device_raw, metadata=metadata)
            elif device_type == ASSET_TYPE:
                device = self._create_asset_device(device_raw=device_raw, metadata=metadata)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
