import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field, JsonStringFormat
from axonius.utils.files import get_local_config_file

from axonius.clients.tanium import tools

from tanium_adapter.connection import TaniumPlatformConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        server_name = Field(field_type=str, title='Server')
        server_version = Field(field_type=str, title='Server Version', json_format=JsonStringFormat.version)
        ip_client = Field(field_type=str, title='Agent IP Address Client')
        ip_server = Field(field_type=str, title='Agent IP Address Server')
        last_reg = Field(field_type=datetime.datetime, title='Agent Last Registration')
        port_number = Field(field_type=int, title='Agent Port Number')
        protocol_version = Field(field_type=str, title='Agent Protocol Version')
        public_key_valid = Field(field_type=bool, title='Agent Public Key Valid')
        receive_state = Field(field_type=str, title='Agent Receive State')
        send_state = Field(field_type=str, title='Agent Send State')
        status = Field(field_type=str, title='Agent Status')
        using_tls = Field(field_type=bool, title='Agent Using TLS')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain'] + '_' + client_config['username']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(
            client_config.get('domain'), https_proxy=client_config.get('https_proxy')
        )

    @staticmethod
    def get_connection(client_config):
        connection = TaniumPlatformConnection(
            domain=client_config['domain'],
            verify_ssl=client_config['verify_ssl'],
            username=client_config['username'],
            password=client_config['password'],
            https_proxy=client_config.get('https_proxy'),
        )
        with connection:
            connection.advanced_connect(client_config=client_config)
        return connection

    def _connect_client(self, client_config):
        domain = client_config.get('domain')
        try:
            return self.get_connection(client_config), client_config
        except RESTException as exc:
            msg = f'Error connecting to client at {domain!r}, reason: {exc}'
            logger.exception(msg)
            raise ClientConnectionException(msg)

    def _query_devices_by_client(self, client_name, client_data):
        connection, client_config = client_data
        with connection:
            yield from connection.get_device_list(client_name=client_name, client_config=client_config)

    @staticmethod
    def _stat_get_hostname(device_raw):
        try:
            hostname = device_raw.get('host_name')
            if hostname and hostname.endswith('(none)'):
                hostname = hostname[: -len('(none)')]
            return hostname or ''
        except Exception:
            logger.exception(f'problem getting host_name from {device_raw!r}')
        return ''

    @staticmethod
    def _stat_agent(device, device_raw):
        value = device_raw.get('full_version')

        try:
            device.add_agent_version(agent=AGENT_NAMES.tanium, version=value)
        except Exception:
            logger.exception(f'Problem adding value {value!r} from {device_raw!r}')

    @staticmethod
    def _stat_last_reg(device, device_raw):
        value = tools.parse_dt(device_raw.get('last_registration'))

        try:
            device.last_seen = value
        except Exception:
            logger.exception(f'Problem adding value {value!r} from {device_raw!r}')

        try:
            device.last_reg = value
        except Exception:
            logger.exception(f'Problem adding value {value!r} from {device_raw!r}')

    @staticmethod
    def _stat_nic(device, device_raw):
        ip_client = tools.parse_ip(device_raw.get('ipaddress_client'))
        ip_server = tools.parse_ip(device_raw.get('ipaddress_server'))

        try:
            device.add_nic(mac=None, ips=tools.listify(ip_client))
        except Exception:
            logger.exception(f'Problem adding nic {ip_client!r} from {device_raw!r}')

        try:
            device.ip_client = ip_client
        except Exception:
            logger.exception(f'Problem adding ip_client {ip_client!r} from {device_raw!r}')

        try:
            device.ip_server = ip_server
        except Exception:
            logger.exception(f'Problem adding ip_server {ip_server!r} from {device_raw!r}')

    @staticmethod
    def _stat_maps(device, device_raw):
        int_map = {'port_number': 'port_number'}

        bool_map = {
            'public_key_valid': 'public_key_valid',
            'registered_with_tls': 'using_tls',
        }

        str_map = {
            'send_state': 'send_state',
            'receive_state': 'receive_state',
            'status': 'status',
            'protocol_version': 'protocol_version',
        }

        for key, attr in int_map.items():
            if key not in device_raw:
                logger.error(f'Missing int key {key!r} in device_raw {device_raw!r}')
                continue
            value = tools.parse_int(device_raw.get(key))
            setattr(device, attr, value)

        for key, attr in str_map.items():
            if key not in device_raw:
                logger.error(f'Missing str key {key!r} in device_raw {device_raw!r}')
                continue

            value = device_raw.get(key)
            setattr(device, attr, value)

        for key, attr in bool_map.items():
            if key not in device_raw:
                logger.error(f'Missing bool key {key!r} in device_raw {device_raw!r}')
                continue

            value = tools.parse_bool(device_raw.get(key))
            setattr(device, attr, value)

    def _create_stat_device(self, device_raw, metadata):
        cid_attr = 'computer_id'

        if cid_attr not in device_raw:
            msg = f'NO {cid_attr!r} ATTR DEFINED IN {device_raw!r}'
            logger.error(msg)
            return None

        cid = device_raw.get('computer_id')
        cid = str(cid) if cid else None

        if not cid:
            msg = f'EMPTY VALUE IN {cid_attr!r} ATTR IN {device_raw!r}'
            logger.error(msg)
            return None

        device = self._new_device_adapter()

        hostname = self._stat_get_hostname(device_raw)
        dvc_id = '_'.join([cid, hostname])

        device.id = dvc_id
        device.uuid = cid
        device.hostname = hostname or None

        tools.set_metadata(device=device, metadata=metadata)
        self._stat_agent(device=device, device_raw=device_raw)
        self._stat_last_reg(device=device, device_raw=device_raw)
        self._stat_nic(device=device, device_raw=device_raw)
        self._stat_maps(device=device, device_raw=device_raw)

        device.set_raw(device_raw)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, metadata in devices_raw_data:
            device = None
            try:
                device = self._create_stat_device(device_raw=device_raw, metadata=metadata)
            except Exception:
                logger.exception(f'Problem with creating System Status Device {device_raw!r}')

            if device:
                yield device

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {'name': 'domain', 'title': 'Hostname or IP Address', 'type': 'string'},
                {'name': 'username', 'title': 'User Name', 'type': 'string'},
                {'name': 'password', 'title': 'Password', 'type': 'string', 'format': 'password'},
                {
                    'name': 'last_reg_mins',
                    'type': 'integer',
                    'title': 'Only fetch clients that have registered in the past N minutes',
                    'default': 60,
                },
                {'name': 'verify_ssl', 'title': 'Verify SSL', 'type': 'bool'},
                {'name': 'https_proxy', 'title': 'HTTPS Proxy', 'type': 'string'},
            ],
            'required': ['domain', 'username', 'password', 'verify_ssl'],
            'type': 'array',
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
