# pylint: disable=E0401
import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import normalize_var_name, format_ip
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field, ListField, JsonStringFormat
from tanium_adapter.connection import TaniumConnection
from tanium_adapter.consts import ENDPOINT_TYPE, DISCOVERY_TYPE, DISCOVER_METHODS, SQ_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


def map_tanium_value_type(value, value_type: str):
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
    if not isinstance(value, (tuple, list, str)) or value in [[], None, '']:
        return None

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
    elif value_type == 'IPAddress':
        field_args['converter'] = format_ip
        field_args['json_format'] = JsonStringFormat.ip
    return value, field_args


# pylint: disable=R0912
def put_tanium_dynamic_field(entity: SmartJsonClass, name: str, value_map: dict, is_sub_field: bool = False):
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
                put_tanium_dynamic_field(entity=smartjsonclass_instance, name=d_key, value_map=d_map, is_sub_field=True)

            entity[key].append(smartjsonclass_instance)
    else:
        if not entity.does_field_exist(field_name=key):
            try:
                value, field_args = map_tanium_value_type(value=value, value_type=value_type)
            except Exception:
                logger.exception(f'Failed to map value {value} with type {value_type}')
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
        tanium_type = Field(str, 'Tanium Device Type', enum=[ENDPOINT_TYPE, DISCOVERY_TYPE, SQ_TYPE])
        created_at = Field(datetime.datetime, 'Discover Created At')
        updated_at = Field(datetime.datetime, 'Discover Updated At')
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

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = TaniumConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      username=client_config['username'],
                                      password=client_config['password'],
                                      https_proxy=client_config.get('https_proxy'))
        with connection:
            fetch_discovery = (client_config.get('fetch_discovery') or False)
            connection.advanced_connect(sq_name=client_config.get('sq_name'), fetch_discovery=fetch_discovery)
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
        sq_name = client_config.get('sq_name')
        sq_max_hours = (client_config.get('sq_max_hours') or 0)
        sq_refresh = (client_config.get('sq_refresh') or False)
        with connection:
            yield from connection.get_device_list(fetch_discovery=fetch_discovery,
                                                  sq_name=sq_name,
                                                  sq_max_hours=sq_max_hours,
                                                  sq_refresh=sq_refresh)

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
                    'name': 'fetch_discovery',
                    'type': 'bool',
                    'title': 'Fetch devices from Tanium Discover Module'
                },
                {
                    'name': 'sq_name',
                    'type': 'string',
                    'title': 'Saved Question Name'
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
                'fetch_discovery'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_endpoint_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device.tanium_type = ENDPOINT_TYPE
            device_id = device_raw.get('computer_id')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
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
            logger.exception(f'Problem with fetching Tanium Device {device_raw}')
            return None

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_discovery_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device.tanium_type = DISCOVERY_TYPE
            device_id = device_raw.get('macaddress')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + str(device_raw.get('computerid'))
            ips = [device_raw.get('ipaddress')] if device_raw.get('ipaddress') else None
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
            device.updated_at = parse_date(device_raw.get('updatedAt'))
            device.last_seen = parse_date(device_raw.get('lastDiscoveredAt'))
            device.created_at = parse_date(device_raw.get('createdAt'))
            device.first_seen = parse_date(device_raw.get('createdAt'))
            if isinstance(device_raw.get('unmanageable'), int):
                device.unmanageable = device_raw.get('unmanageable') == 1
            if isinstance(device_raw.get('ismanaged'), int):
                device.is_managed = device_raw.get('ismanaged') == 1
            if isinstance(device_raw.get('ignored'), int):
                device.ignored = device_raw.get('ignored') == 1
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Tanium Device {device_raw}')
            return None

    # pylint: disable=too-many-branches,too-many-locals
    def _create_sq_device(self, device_raw):
        def _check_sensor_data_one_item(sensor_data):
            if not sensor_data.get('value') or not isinstance(sensor_data.get('value'), list):
                return None
            return sensor_data.get('value')[0]

        def _check_sensor_data_full_list(sensor_data):
            if not sensor_data.get('value') or not isinstance(sensor_data.get('value'), list) \
                    or sensor_data.get('value')[0] == '[no results]':
                return None
            return sensor_data.get('value')

        try:
            device_raw, sq_name, question = device_raw
            device = self._new_device_adapter()
            device.tanium_type = SQ_TYPE
            device.sq_name = sq_name
            device.sq_query_text = question.get('query_text')
            device.sq_expiration = parse_date(question.get('expiration'))

            try:
                device.sq_selects = [x.get('sensor', {}).get('name') for x in question.get('selects', [])]
            except Exception:
                logger.exception(f'Problem with parsing sensors from selects in question {question}')

            if 'Computer ID' not in device_raw:
                logger.warning(f'Bad device with no id {device_raw}')
                return None
            for sensor_name, sensor_data in device_raw.items():
                try:
                    if sensor_name == 'Computer ID':
                        computer_id = _check_sensor_data_one_item(sensor_data)
                        if not computer_id:
                            logger.warning(f'Bad device with no id {device_raw}')
                            return None
                        computer_id = str(computer_id)
                        device.id = 'SQ_DEVICE' + '_' + computer_id
                        device.uuid = computer_id
                    elif sensor_name == 'Computer Name':
                        device.hostname = _check_sensor_data_one_item(sensor_data)
                    elif sensor_name == 'Computer Serial Number':
                        device.device_serial = _check_sensor_data_one_item(sensor_data)
                    elif sensor_name in ['IP Address', 'IPv4 Address', 'IPv6 Address', 'Static IP Addresses']:
                        device.add_nic(ips=_check_sensor_data_full_list(sensor_data))
                    elif sensor_name == 'Installed Applications':
                        apps_raw = _check_sensor_data_full_list(sensor_data) or []
                        for app_raw in apps_raw:
                            try:
                                app_name = (app_raw.get('Name') or {}).get('value')
                                app_version = (app_raw.get('Version') or {}).get('value')
                                device.add_installed_software(name=app_name,
                                                              version=app_version)
                            except Exception:
                                logger.exception(f'Problem with app raw {app_raw}')
                    elif sensor_name == 'Chassis Type':
                        device.chassis_type = _check_sensor_data_one_item(sensor_data)
                    elif sensor_name == 'Last Logged In User':
                        device.last_used_users = _check_sensor_data_full_list(sensor_data)
                    elif sensor_name == 'Last Reboot':
                        device.set_boot_time(boot_time=parse_date(_check_sensor_data_one_item(sensor_data)))
                    elif sensor_name == 'Model':
                        device.device_model = _check_sensor_data_one_item(sensor_data)
                    elif sensor_name == 'Manufacturer':
                        device.device_manufacturer = _check_sensor_data_one_item(sensor_data)
                    elif sensor_name == 'Custom Tags':
                        if _check_sensor_data_one_item(sensor_data) \
                                and _check_sensor_data_one_item(sensor_data) != '[No Tags]':
                            device.sensor_tags = _check_sensor_data_full_list(sensor_data)
                    elif sensor_name == 'CPU Details':
                        cpu_data = _check_sensor_data_one_item(sensor_data)
                        if not isinstance(cpu_data, dict):
                            cpu_data = {}
                        device.add_cpu(name=(cpu_data.get('CPU') or {}).get('value'),
                                       cores=int((cpu_data.get('Total Cores') or {}).get('value')))
                    elif sensor_name == 'Network Adapters':
                        nics_raw = _check_sensor_data_full_list(sensor_data)
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
                        device.figure_os(_check_sensor_data_one_item(sensor_data))
                    elif sensor_name == 'Service Details':
                        for service_raw in _check_sensor_data_full_list(sensor_data) or []:
                            display_name = (service_raw.get('Service Display Name') or {}).get('value')
                            service_status = (service_raw.get('Service Status') or {}).get('value')
                            service_name = (service_raw.get('Service Name') or {}).get('value')
                            device.add_service(display_name=display_name,
                                               name=service_status,
                                               status=service_name)
                except Exception:
                    logger.exception(f'Problem with sensor name {sensor_name}')

                try:
                    put_tanium_dynamic_field(entity=device, name=sensor_name, value_map=sensor_data, is_sub_field=False)
                except Exception:
                    logger.exception(f'Failed putting key {sensor_name!r} with value {sensor_data!r}')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Tanium Device {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == ENDPOINT_TYPE:
                device = self._create_endpoint_device(device_raw)
            elif device_type == DISCOVERY_TYPE:
                device = self._create_discovery_device(device_raw)
            elif device_type == SQ_TYPE:
                device = self._create_sq_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
