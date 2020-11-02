import logging

import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field, JsonStringFormat, ListField
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import format_ip, format_ip_raw
from microfocus_sa_adapter.connection import MicrofocusSaConnection
from microfocus_sa_adapter.consts import STR_FIELDS, DT_FIELDS, BOOL_FIELDS, IP_FIELDS

logger = logging.getLogger(f'axonius.{__name__}')


def parse_date_type(obj):
    if obj:
        try:
            return parse_date(obj)
        except Exception:
            msg = f'Failed to parse date {obj}'
            logger.exception(msg)
            return None
    return obj


def parse_ip_type(obj, is_raw=False):
    if obj:
        try:
            if is_raw:
                return format_ip_raw(obj)
            return format_ip(obj)
        except Exception:
            msg = f'Failed to parse IP address {obj}'
            logger.exception(msg)
            return None
    return obj


def add_field_server_version(device, metadata):
    # this isn't a pure "version" field - it looks like:
    # SAS 10.70.000 Opsware API
    try:
        server_version = metadata.get('server_version', None) or None
        device.server_version = server_version
    except Exception:
        msg = f'Failed to parse server version from metadata {metadata}'
        logger.exception(msg)


def add_fields_str(device, device_raw):
    for k, v in STR_FIELDS.items():
        try:
            setattr(device, k, device_raw.get(v, None) or None)
        except Exception:
            msg = f'Error adding device attr {k!r} from raw STR attr {v!r}'
            logger.exception(msg)


def add_fields_dt(device, device_raw):
    for k, v in DT_FIELDS.items():
        try:
            setattr(device, k, parse_date_type(device_raw.get(v, None) or None))
        except Exception:
            msg = f'Error adding device attr {k!r} from raw DATETIME attr {v!r}'
            logger.exception(msg)


def add_fields_bool(device, device_raw):
    for k, v in BOOL_FIELDS.items():
        try:
            setattr(device, k, device_raw.get(v, None))
        except Exception:
            msg = f'Error adding device attr {k!r} from raw BOOL attr {v!r}'
            logger.exception(msg)


def add_fields_ips(device, device_raw):
    for field_name, provider_field_name in IP_FIELDS.items():
        try:
            field_value = device_raw.get(provider_field_name) or None
            setattr(device, field_name, parse_ip_type(field_value))
            if isinstance(field_value, str):
                field_value = [field_value]
            setattr(device, f'{field_name}_raw', parse_ip_type(field_value, is_raw=True))
        except Exception:
            logger.exception(f'Error adding device attr {field_name!r} from raw IP attr {provider_field_name!r}')


def add_field_complex_agent(device, device_raw):
    try:
        agent_version = device_raw.get('agentVersion', None) or None
        device.add_agent_version(agent=AGENT_NAMES.microfocus_sa, version=agent_version)
    except Exception:
        msg = f'Error adding agent version from {device_raw}'
        logger.exception(msg)


def add_field_complex_os(device, device_raw):
    try:
        os_string = device_raw.get('platform', None) or None
        device.figure_os(os_string=os_string)
    except Exception:
        msg = f'Error adding OS info from {device_raw}'
        logger.exception(msg)


def add_field_complex_nics(device, device_raw):
    try:
        ips = device_raw.get('primaryIP', None) or None
        ips = [ips] if ips else []
        gateway = device_raw.get('defaultGw', None) or None
        device.add_nic(ips=ips, gateway=gateway)
    except Exception:
        msg = f'Error adding NIC from {device_raw}'
        logger.exception(msg)


def add_fields_complex(device, device_raw):
    add_field_complex_agent(device=device, device_raw=device_raw)
    add_field_complex_os(device=device, device_raw=device_raw)
    add_field_complex_nics(device=device, device_raw=device_raw)


class MicrofocusSaAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        agent_ver = Field(field_type=str, title='SA Agent Version', json_format=JsonStringFormat.version)
        created_by = Field(field_type=str, title='Created By')
        created_dt = Field(field_type=datetime.datetime, title='Created Date')
        customer = Field(field_type=str, title='Customer')
        default_gw = Field(
            field_type=str, title='Default Gateway', converter=format_ip, json_format=JsonStringFormat.ip
        )
        default_gw_raw = ListField(field_type=str, converter=format_ip_raw, hidden=True)
        default_gw_ipv6 = Field(
            field_type=str, title='Default Gateway IPv6', converter=format_ip, json_format=JsonStringFormat.ip
        )
        default_gw_ipv6_raw = ListField(field_type=str, converter=format_ip_raw, hidden=True)
        discovered_date = Field(field_type=datetime.datetime, title='Discovered Date')
        facility = Field(field_type=str, title='Facility')
        first_detect_dt = Field(field_type=datetime.datetime, title='First Detected Date')
        hypervisor = Field(field_type=bool, title='Is Hypervisor')
        last_reg_dt = Field(field_type=datetime.datetime, title='Last Registration Date')
        last_scan_dt = Field(field_type=datetime.datetime, title='Last Scan Date')
        lifecycle = Field(field_type=str, title='Lifecycle')
        locale = Field(field_type=str, title='Locale')
        log_change = Field(field_type=bool, title='Is Logging Changes')
        loopback_ip = Field(field_type=str, title='Loopback IP', converter=format_ip, json_format=JsonStringFormat.ip)
        loopback_ip_raw = ListField(field_type=str, converter=format_ip_raw, hidden=True)
        management_ip = Field(
            field_type=str, title='Management IP', converter=format_ip, json_format=JsonStringFormat.ip
        )
        management_ip_raw = ListField(field_type=str, converter=format_ip_raw, hidden=True)
        modified_date = Field(field_type=datetime.datetime, title='Modified Date')
        netbios_name = Field(field_type=str, title='Netbios Name')
        origin = Field(field_type=str, title='Origin')
        os_flavor = Field(field_type=str, title='Operating System Flavor')
        os_platform = Field(field_type=str, title='Operating System Platform')
        os_service_pack = Field(field_type=str, title='Operating System Service Pack')
        os_version = Field(field_type=str, title='Operating System Version')
        peer_ip = Field(field_type=str, title='Peer IP', converter=format_ip, json_format=JsonStringFormat.ip)
        peer_ip_raw = ListField(field_type=str, converter=format_ip_raw, hidden=True)
        primary_ip = Field(field_type=str, title='Primary IP', converter=format_ip, json_format=JsonStringFormat.ip)
        primary_ip_raw = ListField(field_type=str, converter=format_ip_raw, hidden=True)
        realm = Field(field_type=str, title='Realm')
        reboot_required = Field(field_type=bool, title='Is Reboot Required')
        reporting = Field(field_type=bool, title='Is Reporting')
        server_version = Field(field_type=str, title='SA Server Version')
        stage = Field(field_type=str, title='Stage')
        state = Field(field_type=str, title='State')
        use = Field(field_type=str, title='Use')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        domain = client_config['domain']
        return domain

    @staticmethod
    def _test_reachability(client_config):
        domain = client_config.get('domain')
        https_proxy = client_config.get('https_proxy')
        return RESTConnection.test_reachability(host=domain, https_proxy=https_proxy)

    @staticmethod
    def get_connection(client_config):
        connection = MicrofocusSaConnection(
            domain=client_config['domain'],
            verify_ssl=client_config['verify_ssl'],
            username=client_config['username'],
            password=client_config['password'],
            https_proxy=client_config.get('https_proxy'),
        )
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {'name': 'domain', 'title': 'Hostname or IP Address', 'type': 'string'},
                {'name': 'username', 'title': 'User Name', 'type': 'string'},
                {'name': 'password', 'title': 'Password', 'type': 'string', 'format': 'password'},
                {'name': 'verify_ssl', 'title': 'Verify SSL', 'type': 'bool'},
                {'name': 'https_proxy', 'title': 'HTTPS Proxy', 'type': 'string'},
            ],
            'required': ['domain', 'username', 'password', 'verify_ssl'],
            'type': 'array',
        }

    def _create_device(self, device_raw, metadata):
        try:
            device = self._new_device_adapter()
            mid = device_raw.get('mid')  # str

            if mid is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            device.id = '_'.join([x for x in [mid, device_raw.get('hostName') or None] if x])
            add_field_server_version(device=device, metadata=metadata)
            add_fields_complex(device=device, device_raw=device_raw)
            add_fields_str(device=device, device_raw=device_raw)
            add_fields_dt(device=device, device_raw=device_raw)
            add_fields_bool(device=device, device_raw=device_raw)
            add_fields_ips(device=device, device_raw=device_raw)
            device.set_raw(raw_data=device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching MicrofocusSa Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device_raw, metadata = device_raw
            device = self._create_device(device_raw=device_raw, metadata=metadata)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
