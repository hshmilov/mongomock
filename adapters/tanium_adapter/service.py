import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, JsonStringFormat, ListField
from axonius.utils.files import get_local_config_file

from axonius.clients import tanium

from tanium_adapter.connection import TaniumPlatformConnection

logger = logging.getLogger(f'axonius.{__name__}')


class ModuleInfo(SmartJsonClass):
    label = Field(field_type=str, title='Name')
    last_install = Field(field_type=datetime.datetime, title='Last Install Date')
    version = Field(field_type=str, title='Version', json_format=JsonStringFormat.version)


class TaniumAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        server_name = Field(field_type=str, title='Tanium Server')
        server_version = Field(field_type=str, title='Tanium Server Version', json_format=JsonStringFormat.version)
        ip_client = Field(field_type=str, title='Agent IP Address Client')
        ip_server = Field(field_type=str, title='Agent IP Address Server')
        last_registration = Field(field_type=datetime.datetime, title='Agent Last Registration')
        port_number = Field(field_type=int, title='Agent Port Number')
        protocol_version = Field(field_type=str, title='Agent Protocol Version')
        public_key_valid = Field(field_type=bool, title='Agent Public Key Valid')
        receive_state = Field(field_type=str, title='Agent Receive State')
        send_state = Field(field_type=str, title='Agent Send State')
        status = Field(field_type=str, title='Agent Status')
        using_tls = Field(field_type=bool, title='Agent Using TLS')
        computer_id = Field(field_type=int, title='Agent Computer ID')
        installed_modules = ListField(field_type=ModuleInfo, title='Installed Modules')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return tanium.tools.joiner(client_config['domain'], client_config['username'], join='_',)

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
            raise ClientConnectionException(f'Error connecting to client at {domain!r}, reason: {exc}')

    def _query_devices_by_client(self, client_name, client_data):
        connection, client_config = client_data
        with connection:
            yield from connection.get_device_list(client_name=client_name, client_config=client_config)

    @staticmethod
    def _get_hostname(device_raw):
        value = device_raw.get('host_name')
        try:
            if value:
                if value.endswith('(none)'):
                    value = value[: -len('(none)')]
                if './bin/sh' in value:
                    value = value[:value.find('./bin/sh')]
            return value or ''
        except Exception:
            logger.exception(f'ERROR getting host_name from {value!r} from {list(device_raw)}')
        return ''

    @staticmethod
    def _add_agent(device, device_raw, key, attr):
        value = device_raw.get(key)
        src = {'value': value, 'key': key, 'attr': attr}
        value = tanium.tools.parse_str(value=value, src=src)

        if not tanium.tools.is_empty(value=value):
            device.add_agent_version(agent=AGENT_NAMES.tanium, version=value)

    @staticmethod
    def _add_nic(device, device_raw, key, attr):
        value = device_raw.get(key)
        src = {'value': value, 'key': key, 'attr': attr}
        value = tanium.tools.parse_ip(value=value, src=src)
        value = tanium.tools.listify(value=value, clean=True)

        if not tanium.tools.is_empty(value=value):
            device.add_nic(mac=None, ips=value)

    @staticmethod
    def _set_modules(device, metadata):
        try:
            workbenches = metadata.get('workbenches', {})
            skips = ['CommonUIComponents']

            for workname, workmeta in workbenches.items():

                label = workmeta.get('label')

                if not label or label in skips:
                    continue

                version = workmeta.get('version')

                last_install = workmeta.get('last_install')
                last_install = tanium.tools.parse_str(value=last_install, src=workmeta)
                last_install = last_install[:10] if last_install else None
                last_install = tanium.tools.parse_dt(value=last_install, src=workmeta)

                kwargs = dict(last_install=last_install, label=label, version=version)

                if not tanium.tools.is_empty_vals(value=kwargs):
                    try:
                        device.installed_modules.append(ModuleInfo(**kwargs))
                    except Exception:
                        logger.exception(f'ERROR workname {workname!r} workmeta {workmeta!r} kwargs {kwargs!r}')
        except Exception:
            logger.exception(f'ERROR metadata {metadata!r}')

    @property
    def key_attr_map(self):
        """Maps keys in device_raw to attributes to set on device adapter and method to use.

        (key in device_raw to get value from, attr to set value on device, method to use to set value on attr)
        """
        aggregated = [
            ('full_version', None, self._add_agent),
            ('ipaddress_client', None, self._add_nic),
            ('last_registration', 'last_seen', tanium.tools.set_dt),
        ]
        specific = [
            ('computer_id', 'computer_id', tanium.tools.set_int),
            ('ipaddress_client', 'ip_client', tanium.tools.set_ip),
            ('ipaddress_server', 'ip_server', tanium.tools.set_ip),
            ('last_registration', 'last_registration', tanium.tools.set_dt),
            ('port_number', 'port_number', tanium.tools.set_int),
            ('protocol_version', 'protocol_version', tanium.tools.set_str),
            ('public_key_valid', 'public_key_valid', tanium.tools.set_bool),
            ('receive_state', 'receive_state', tanium.tools.set_str),
            ('registered_with_tls', 'using_tls', tanium.tools.set_bool),
            ('send_state', 'send_state', tanium.tools.set_str),
            ('status', 'status', tanium.tools.set_str),
        ]
        return aggregated + specific

    def _create_stat_device(self, device_raw, metadata):
        cid_key = 'computer_id'
        cid = device_raw.get(cid_key)
        cid = tanium.tools.parse_str(value=cid, src=cid_key)

        id_map = {cid_key: cid}
        if tanium.tools.is_empty_vals(value=id_map):
            logger.error(f'Bad device with empty ids {id_map} in {device_raw}')
            return None

        device = self._new_device_adapter()
        hostname = self._get_hostname(device_raw=device_raw)
        device.id = tanium.tools.joiner(cid, hostname, join='_')
        device.uuid = cid
        device.hostname = hostname
        tanium.tools.handle_key_attr_map(self=self, device=device, device_raw=device_raw)
        tanium.tools.set_metadata(device=device, metadata=metadata)
        self._set_modules(device=device, metadata=metadata)
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
