import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.dynamic_fields import put_dynamic_field
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.consts.csv_consts import get_csv_field_names
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.clients.splunk.connection import SplunkConnection

logger = logging.getLogger(f'axonius.{__name__}')


DEVICES_NEEDED_FIELDS = ['id', 'serial', 'mac_address', 'hostname', 'name']


class SplunkAdapter(AdapterBase, Configurable):

    class MyDeviceAdapter(DeviceAdapter):
        vlan = Field(str, 'Vlan')
        port = Field(str, 'port')
        cisco_device = Field(str, 'Cisco Device')
        device_type = Field(str, 'Device Type')
        splunk_source = Field(str, "Splunk Source")
        vpn_source_ip = Field(str, 'VPN Source IP')
        agent_id = Field(str, 'Agent ID')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return '{}:{}'.format(client_config['host'], client_config['port'])

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("host"), client_config.get("port"))

    def _connect_client(self, client_config):
        has_token = bool(client_config.get('token'))
        maybe_has_user = bool(client_config.get('username')) or bool(client_config.get('password'))
        has_user = bool(client_config.get('username')) and bool(client_config.get('password'))
        if has_token and maybe_has_user:
            msg = f"Different logins for Splunk domain " \
                  f"{client_config.get('host')}, user: {client_config.get('username', '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        elif maybe_has_user and not has_user:
            msg = f"Missing credentials for Splunk [] domain " \
                  f"{client_config.get('host')}, user: {client_config.get('username', '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        try:
            connection = SplunkConnection(**client_config)
            with connection:
                pass
            return connection
        except Exception as e:
            message = "Error connecting to client {0}, reason: {1}".format(self._get_client_id(client_config), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Splunk domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Splunk connection

        :return: A json with all the attributes returned from the Splunk Server
        """
        with client_data:
            yield from client_data.get_devices(f'-{self.__max_log_history}d',
                                               self.__maximum_records,
                                               self.__fetch_plugins,
                                               splunk_macros_list=self.__splunk_macros_list,
                                               splunk_sw_macros_list=self.__splunk_sw_macros_list)

    def _clients_schema(self):
        """
        The schema SplunkAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "host",
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": "port",
                    "title": "Port",
                    "type": "integer",
                    "format": "port"
                },
                {
                    'name': 'scheme',
                    'title': 'Protocol',
                    'type': 'string',
                    'enum': ['http', 'https'],
                    'default': 'https'
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "token",
                    "title": "API Token",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                "host",
                "port",
                'scheme'
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        macs_set = set()
        dhcp_ids_sets = set()
        vpn_ids_sets = set()
        landdesk_ids_sets = set()
        nexpose_asset_id_set = set()
        hostname_sw_dict = dict()

        for device_raw, device_type in devices_raw_data:
            try:
                device = self._new_device_adapter()
                raw_splunk_insertion_time = device_raw.get('raw_splunk_insertion_time')
                if raw_splunk_insertion_time:
                    device.last_seen = parse_date(raw_splunk_insertion_time)
                if 'DHCP' in device_type:
                    device.adapter_properties = [AdapterProperty.Network.name]
                    mac = device_raw.get('mac')
                    hostname = device_raw.get('hostname')
                    if not mac and not hostname:
                        logger.warning(f'Bad device no mac or hostname{device_raw}')
                        continue

                    if mac:
                        device_id = (hostname or '') + '_' + mac + device_type
                    else:
                        device_id = hostname + device_type

                    if device_id in dhcp_ids_sets:
                        continue

                    device.id = device_id
                    device.hostname = hostname
                    ip = device_raw.get('ip')
                    macs = []
                    if len(mac) > 12 and len(mac) % 12 == 0:
                        while mac != '':
                            macs.append(mac[:12])
                            mac = mac[12:]
                    else:
                        macs = [mac]
                    ips = ip.split(',') if ip and isinstance(ip, str) else []
                    device.add_ips_and_macs(macs, ips)
                    device.description = device_raw.get('description')
                    dhcp_ids_sets.add(device_id)
                    device.splunk_source = "AD DHCP"

                elif 'Cisco' in device_type:
                    device.adapter_properties = [AdapterProperty.Network.name]
                    mac = device_raw.get('mac')
                    if not mac:
                        logger.warning(f'Bad device no MAC {device_raw}')
                        continue
                    if mac in macs_set:
                        continue
                    device.id = mac + device_type
                    ip = device_raw.get('ip')
                    if not ip:
                        device.add_nic(mac, None)
                    else:
                        device.add_nic(mac, [ip])
                    device.vlan = device_raw.get('vlan')
                    device.port = device_raw.get('port')
                    device.cisco_device = device_raw.get('cisco_device')
                    macs_set.add(mac)
                    device.splunk_source = "Cisco"
                elif 'VPN' in device_type:
                    device.adapter_properties = [AdapterProperty.Network.name]
                    hostname = device_raw.get('hostname')
                    if not hostname:
                        logger.warning(f'Bad device no hostname {device_raw}')
                        continue
                    device_id = hostname + device_type
                    if device_id in vpn_ids_sets:
                        continue
                    device.id = device_id
                    device.hostname = hostname
                    ip = device_raw.get('ip')
                    if ip:
                        device.add_nic(None, [ip])
                    vpn_ids_sets.add(device_id)
                    device.vpn_source_ip = device_raw.get('vpn_source_ip')
                    device.splunk_source = 'VPN'
                elif 'Windows Login' in device_type:
                    device.adapter_properties = [AdapterProperty.Manager.name]
                    hostname = device_raw.get('hostname')
                    if not hostname:
                        logger.warning(f'Bad device no hostname {device_raw}')
                        continue
                    device.id = hostname + device_type
                    device.hostname = hostname
                    users = device_raw.get('users')
                    if users:
                        device.last_used_users = users

                    device.splunk_source = 'Windows Login'
                elif 'Splunk agent version' in device_type:
                    device.adapter_properties = [AdapterProperty.Manager.name]
                    hostname = device_raw.get('hostname')
                    if not hostname:
                        logger.warning(f'Bad device no hostname {device_raw}')
                        continue
                    device.id = hostname + device_type
                    device.hostname = hostname
                    device.add_agent_version(agent=AGENT_NAMES.splunk,
                                             version=device_raw.get('agent_version'))
                    device.last_seen = parse_date(device_raw.get('last_seen'))
                    device.agent_id = device_raw.get('agent_id')
                    device.splunk_source = 'Splunk agent version'
                elif 'Nexpose' in device_type:
                    device.adapter_properties = [AdapterProperty.Network.name,
                                                 AdapterProperty.Vulnerability_Assessment.name]
                    device_id = device_raw['asset_id']
                    if device_id in nexpose_asset_id_set:
                        continue
                    nexpose_asset_id_set.add(device_id)
                    device.id = device_raw['asset_id']
                    device.hostname = device_raw.get('hostname')
                    device.figure_os(device_raw.get('version') or device_raw.get('os'))
                    try:
                        device.add_nic(device_raw.get('mac'), [device_raw.get('ip')])
                    except Exception:
                        logger.exception(f"Couldn't add nic to device {device_raw}")
                    device.splunk_source = "Nexpose"
                elif 'Landesk' in device_type:
                    device.splunk_source = 'Landesk'
                    device.adapter_properties = [AdapterProperty.Agent.name]
                    hostname = device_raw.get('hostname')
                    if not hostname:
                        logger.warning(f'Bad landesk device with no hostname {device_raw}')
                        continue
                    id_to_set = hostname + '_' + (device_raw.get('mac') or '')
                    if id_to_set in landdesk_ids_sets:
                        continue
                    landdesk_ids_sets.add(id_to_set)
                    device.id = id_to_set
                    device.hostname = hostname
                    device.domain = device_raw.get('domain')
                    ips = None
                    if device_raw.get('ip'):
                        ip = device_raw.get('ip')
                        ip = '.'.join([str(int(x)) for x in ip.split('.')])
                        ips = [ip]
                    mac = device_raw.get('mac') if device_raw.get('mac') else None
                    if ips or mac:
                        try:
                            device.add_nic(mac, ips)
                        except Exception:
                            logger.exception(f'Problem add nic to {device_raw}')
                    try:
                        device.last_seen = parse_date(device_raw.get('last_seen'))
                    except Exception:
                        logger.exception(f'Problem getting last seen for {device_raw}')
                    try:
                        if device_raw.get('os'):
                            device.figure_os(device_raw.get('os'))
                    except Exception:
                        logger.exception(f'Problem adding os to {device_raw}')
                    try:
                        if device_raw.get('user'):
                            device.last_used_users = [device_raw.get('user')]
                    except Exception:
                        logger.exception(f'Problem adding last used user to {device_raw}')
                    device.device_serial = device_raw.get('serial')
                elif 'PED Macro' == device_type:
                    device.hostname = device_raw.get('hostname')
                    device.device_serial = device_raw.get('serial')
                    device.id = 'PED_' + device_raw.get('hostname')
                    device.splunk_source = 'PED Macro'
                    device.device_type = device_raw.get('type')
                elif 'Store Macro' == device_type:
                    device.add_nic(mac=device_raw.get('mac'), ips=[device_raw.get('ip')])
                    device.id = 'Store_' + device_raw.get('mac')
                    device.bios_version = device_raw.get('bios_version')
                    device.device_serial = device_raw.get('serial')
                    device.splunk_source = 'Store Macro'
                elif device_type.startswith('General Macro '):
                    device.splunk_source = device_type
                    fields = get_csv_field_names(list(device_raw.keys()))
                    if not any(id_field in fields for id_field in DEVICES_NEEDED_FIELDS):
                        logger.debug(f'Bad devices fields names {str(list(device_raw.keys()))}')
                        continue
                    vals = {field_name: device_raw.get(fields[field_name][0]) for field_name in fields}

                    macs = (vals.get('mac_address') or '').split(',')
                    macs = [mac.strip() for mac in macs if mac.strip()]
                    mac_as_id = macs[0] if macs else None

                    device_id = str(vals.get('id', '')) or vals.get('serial') or mac_as_id or vals.get('hostname')
                    if not device_id:
                        logger.debug(f'can not get device id for {device_raw}, continuing')
                        continue

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
                    finalhostname = ''
                    try:
                        finalhostname = device.hostname
                    except Exception:
                        pass
                    device.id = device_type + '_' + device_id + '_' + finalhostname
                    device.device_model = vals.get('model')
                    device.domain = vals.get('domain') or hostname_domain
                    device.last_seen = parse_date(vals.get('last_seen'))
                    device.device_manufacturer = vals.get('manufacturer')
                    try:
                        device.total_physical_memory = vals.get('total_physical_memory_gb')
                    except Exception:
                        pass
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
                    if vals.get('ip') == 'unknown':
                        ips = []

                    if vals.get('username'):
                        device.last_used_users = [vals.get('username')]

                    device.add_ips_and_macs(macs, ips)

                    try:
                        cve_ids = vals.get('cve_id')
                        if isinstance(cve_ids, str) and cve_ids:
                            cve_ids = cve_ids.split(',')
                            for cve_id in cve_ids:
                                device.add_vulnerable_software(cve_id=cve_id)
                    except Exception:
                        logger.warning(f'Problem with cve id', exc_info=True)

                    for column_name, column_value in device_raw.items():
                        try:
                            put_dynamic_field(device, f'splunk_{column_name}', column_value, f'splunk.{column_name}')
                        except Exception:
                            logger.warning(f'Could not parse column {column_name} with value {column_value}',
                                           exc_info=True)
                elif device_type.startswith('Software Macro'):
                    hostname_sw = device_raw.get('hostname')
                    sw_name = device_raw.get('softwarename')
                    sw_version = device_raw.get('softwareversion')
                    sw_vendor = device_raw.get('softwarevendor')
                    if (hostname_sw, device_type) not in hostname_sw_dict:
                        hostname_sw_dict[(hostname_sw, device_type)] = set()
                    hostname_sw_dict[(hostname_sw, device_type)].add((sw_name, sw_version, sw_vendor))
                    continue
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem getting device {device_raw}')
        try:
            for k, v in hostname_sw_dict.items():
                try:
                    hostname_sw, device_type = k
                    sw_list = list(v)
                    device = self._new_device_adapter()
                    device.id = f'{device_type}_{hostname_sw}'
                    device.hostname = hostname_sw
                    device.splunk_source = device_type
                    for sw_raw in sw_list:
                        try:
                            sw_name, sw_version, sw_vendor = sw_raw
                            device.add_installed_software(name=sw_name,
                                                          version=sw_version,
                                                          vendor=sw_vendor)
                        except Exception:
                            logger.exception(f'Problem with sw {sw_raw}')
                    yield device
                except Exception:
                    logger.exception(f'Problem with k {k}')
        except Exception:
            logger.exception(f'Problem getting sw macro')

    def _on_config_update(self, config):
        logger.info(f"Loading Splunk config: {config}")
        self.__max_log_history = int(config['max_log_history'])
        self.__maximum_records = int(config['maximum_records'])
        self.__splunk_macros_list = config.get('splunk_macros_list').split(',') \
            if config.get('splunk_macros_list') else None
        self.__splunk_sw_macros_list = config.get('splunk_sw_macros_list').split(',') \
            if config.get('splunk_sw_macros_list') else None
        self.__fetch_plugins = {
            'nexpose': bool(config['fetch_nexpose']),
            'cisco': config['fetch_cisco'] if 'fetch_cisco' in config else True,
            'win_logs_fetch_hours': int(config['win_logs_fetch_hours']),
            'splunk_agent_version': config['fetch_splunk_agent_version']
            if 'fetch_splunk_agent_version' in config else False
        }

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    'name': 'splunk_macros_list',
                    'title': 'Splunk search macros list',
                    'type': 'string'
                },
                {
                    'name': 'splunk_sw_macros_list',
                    'title': 'Splunk installed software search macros list',
                    'type': 'string'
                },
                {
                    'name': 'max_log_history',
                    'title': 'Number of days to fetch',
                    'type': 'number'
                },
                {
                    "name": "maximum_records",
                    "title": "Maximum amount of records per search",
                    "type": "number"
                },
                {
                    'name': 'win_logs_fetch_hours',
                    'title': 'Windows login hours to fetch',
                    'type': 'number'
                },
                {
                    "name": "fetch_nexpose",
                    "title": "Fetch devices from the splunk-nexpose plugin",
                    "type": "bool"
                },
                {
                    'name': 'fetch_cisco',
                    'title': 'Fetch devices from Cisco',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_splunk_agent_version',
                    'type': 'bool',
                    'title': 'Fetch Splunk agent version'
                }
            ],
            "required": [
                'max_log_history',
                "maximum_records",
                'fetch_cisco',
                'fetch_nexpose',
                'fetch_splunk_agent_version',
                'win_logs_fetch_hours'
            ],
            "pretty_name": "Splunk Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'max_log_history': 30,
            'maximum_records': 100000,
            'fetch_nexpose': False,
            'fetch_cisco': True,
            'fetch_splunk_agent_version': False,
            'splunk_macros_list': None,
            'splunk_sw_macros_list': None,
            'win_logs_fetch_hours': 3
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
