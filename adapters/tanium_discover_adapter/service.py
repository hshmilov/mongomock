import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients import tanium
from axonius.devices.device_adapter import DeviceAdapter, DeviceAdapterOS
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.utils.parsing import figure_out_os
from axonius.utils.files import get_local_config_file
from axonius.mixins.configurable import Configurable
from tanium_discover_adapter.consts import METHODS, FETCH_OPTS, PAGE_SIZE, PAGE_SLEEP

from tanium_discover_adapter.connection import TaniumDiscoverConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumDiscoverAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        server_name = Field(field_type=str, title='Tanium Server')
        server_version = Field(field_type=str, title='Tanium Server Version', json_format=JsonStringFormat.version)
        module_version = Field(field_type=str, title='Module Version', json_format=JsonStringFormat.version)
        tags_cloud = ListField(field_type=str, title='Tags Cloud')
        discover_hostname = Field(field_type=str, title='Discover Hostname')
        tags_discover = ListField(field_type=str, title='Tags Discover')
        computer_id = Field(field_type=int, title='Computer ID')
        created_at = Field(field_type=datetime.datetime, title='Created At')
        os_scanned = Field(field_type=str, title='OS Scanned')
        os_generation = Field(field_type=str, title='OS Generation')
        is_ignored = Field(field_type=bool, title='Is Ignored')
        instance_id = Field(field_type=str, title='Instance ID')
        instance_state = Field(field_type=str, title='Instance State')
        instance_type = Field(field_type=str, title='Instance Type')
        is_managed = Field(field_type=bool, title='Is Managed')
        is_unmanageable = Field(field_type=bool, title='Is Unmanageable')
        last_discovered_at = Field(field_type=datetime.datetime, title='Last Discovered At')
        last_managed_at = Field(field_type=datetime.datetime, title='Last Managed At')
        launch_time = Field(field_type=datetime.datetime, title='Launch Time')
        locations = ListField(field_type=str, title='Locations')
        mac_organization = Field(field_type=str, title='MAC Organization')
        methods_used = ListField(str, 'Methods Used', enum=METHODS)
        nat_ipaddress = Field(field_type=str, title='NAT IP Address', json_format=JsonStringFormat.ip)
        network_id = Field(field_type=str, title='Network ID')
        owner_id = Field(field_type=str, title='Owner ID')
        profile = ListField(field_type=str, title='Profiles Used')
        provider = Field(field_type=str, title='Provider')
        updated_at = Field(field_type=datetime.datetime, title='Updated At')
        zone = Field(field_type=str, title='Zone')
        report_source = Field(field_type=str, title='Report Source')

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
        connection = TaniumDiscoverConnection(
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
            yield from connection.get_device_list(
                client_name=client_name,
                client_config=client_config,
                page_sleep=self._page_sleep,
                page_size=self._page_size,
            )

    @staticmethod
    def _add_nic(device, device_raw, key, attr):
        ips = device_raw.get('ipaddress')
        pips = tanium.tools.parse_csv(ips)
        pips = tanium.tools.parse_ip(pips)
        pips = tanium.tools.listify(pips, clean=True)

        mac = device_raw.get('macaddress')
        pmac = tanium.tools.parse_mac(mac)

        kwargs = dict(mac=pmac, ips=pips)
        if not tanium.tools.is_empty_vals(kwargs):
            device.add_nic(**kwargs)

    @staticmethod
    def _add_adapter_tags(device, device_raw, key, attr):
        values = device_raw.get(key)
        pvalues = tanium.tools.parse_csv(values)

        for value in pvalues:
            try:
                device.add_key_value_tag(key=value, value=None)
            except Exception:
                logger.exception(f'ERROR value {value!r} in {values!r}')

    @staticmethod
    def _add_open_ports(device, device_raw, key, attr):
        values = device_raw.get(key)
        values = tanium.tools.parse_csv(values)
        values = tanium.tools.parse_int(values)
        values = [x for x in values if x > 0]

        for value in values:
            try:
                device.add_open_port(port_id=value)
            except Exception:
                logger.exception(f'ERROR value {value!r} in {values!r}')

    @staticmethod
    def _figure_os(device, device_raw, key, attr):
        os_scan = tanium.tools.parse_str(device_raw.get('os'))
        os_type = figure_out_os(os_scan).get('type')  # Linux

        os_gen = tanium.tools.parse_str(device_raw.get('osgeneration'))

        tags = tanium.tools.parse_csv(device_raw.get('tags'))
        os_tags = tanium.tools.parse_empty([figure_out_os(x).get('type') for x in tags])  # Windows, Linux

        # people add tags to discover assets to denote a different OS type, this handles that
        os_changes = [os_type]
        for os_tag in os_tags:
            if os_tag not in os_changes:
                os_type = os_tag
                os_changes.append(os_tag)

        if os_gen:
            try:
                field = device.get_field_safe(attr='os_guess') or DeviceAdapterOS()
                field.distribution = os_gen
                device.os_guess = field
            except Exception:
                logger.exception(f'ERROR os_gen {os_gen!r} in {device_raw!r}')

        if os_type:
            try:
                device.figure_os(os_type, guess=True)
            except Exception:
                logger.exception(f'ERROR {os_type!r} os_scan {os_scan!r} in {device_raw!r}')

    @staticmethod
    def _set_methods(device, device_raw, key, attr):
        values = device_raw.get(key)
        values = tanium.tools.parse_csv(values)

        values = dict(zip(METHODS, values))
        for value, enabled in values.items():
            try:
                if str(enabled).strip() == '1':
                    device.methods_used.append(value)
            except Exception:
                logger.exception(f'ERROR value {value!r} in {values!r}')

    @property
    def key_attr_map(self):
        """Maps keys in device_raw to attributes to set on device adapter and method to use.

        (key in device_raw to get value from, attr to set value on device, method to use to set value on attr)
        """
        aggregated = [
            ('cloudTags', None, self._add_adapter_tags),
            ('computerid', 'uuid', tanium.tools.set_int),
            ('createdAt', 'first_seen', tanium.tools.set_dt),
            ('ipaddress', None, self._add_nic),
            ('lastDiscoveredAt', 'last_seen', tanium.tools.set_dt),
            ('os', None, self._figure_os),
            ('ports', None, self._add_open_ports),
            ('tags', None, self._add_adapter_tags),
        ]
        if self.__trust_hostname:
            discover_hostname = 'hostname'
        else:
            discover_hostname = 'discover_hostname'
        specific = [
            ('cloudTags', 'tags_cloud', tanium.tools.set_csv),
            ('computerid', 'computer_id', tanium.tools.set_int),
            ('createdAt', 'created_at', tanium.tools.set_dt),
            ('hostname', discover_hostname, tanium.tools.set_str),
            ('ignored', 'is_ignored', tanium.tools.set_bool),
            ('instanceId', 'instance_id', tanium.tools.set_str),
            ('instanceState', 'instance_state', tanium.tools.set_str),
            ('instanceType', 'instance_type', tanium.tools.set_str),
            ('ismanaged', 'is_managed', tanium.tools.set_bool),
            ('lastDiscoveredAt', 'last_discovered_at', tanium.tools.set_dt),
            ('lastManagedAt', 'last_managed_at', tanium.tools.set_dt),
            ('launchTime', 'launch_time', tanium.tools.set_dt),
            ('locations', 'locations', tanium.tools.set_csv),
            ('macorganization', 'mac_organization', tanium.tools.set_str),
            ('method', None, self._set_methods),
            ('natipaddress', 'nat_ipaddress', tanium.tools.set_ip),
            ('networkId', 'network_id', tanium.tools.set_str),
            ('os', 'os_scanned', tanium.tools.set_str),
            ('osgeneration', 'os_generation', tanium.tools.set_str),
            ('ownerId', 'owner_id', tanium.tools.set_str),
            ('profile', 'profile', tanium.tools.set_csv),
            ('provider', 'provider', tanium.tools.set_str),
            ('report_source', 'report_source', tanium.tools.set_str),
            ('tags', 'tags_discover', tanium.tools.set_csv),
            ('unmanageable', 'is_unmanageable', tanium.tools.set_bool),
            ('updatedAt', 'updated_at', tanium.tools.set_dt),
            ('zone', 'zone', tanium.tools.set_str),
        ]
        return aggregated + specific

    def _create_device(self, device_raw, metadata):
        cid_key = 'computerid'
        cid = device_raw.get(cid_key)
        cid = tanium.tools.parse_str(cid)

        mac_key = 'macaddress'
        mac = device_raw.get(mac_key)
        mac = tanium.tools.parse_mac(mac)

        id_map = {cid_key: cid, mac_key: mac}
        if tanium.tools.is_empty_vals(id_map):
            logger.error(f'Bad device with empty ids {id_map} in {device_raw}')
            return None

        device = self._new_device_adapter()
        device.id = tanium.tools.joiner(mac, cid, join='_')
        tanium.tools.set_module_ver(device=device, metadata=metadata, module='discover')
        tanium.tools.set_metadata(device=device, metadata=metadata)
        tanium.tools.handle_key_attr_map(self=self, device=device, device_raw=device_raw)
        device.set_raw(device_raw)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, metadata in devices_raw_data:
            device = None
            try:
                device = self._create_device(device_raw=device_raw, metadata=metadata)
            except Exception:
                logger.exception(f'Problem with parsing device {device_raw}')
            if device:
                yield device

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {'name': 'domain', 'title': 'Hostname or IP Address', 'type': 'string'},
                {'name': 'username', 'title': 'User Name', 'type': 'string'},
                {'name': 'password', 'title': 'Password', 'type': 'string', 'format': 'password'},
                *FETCH_OPTS,
                {'name': 'verify_ssl', 'title': 'Verify SSL', 'type': 'bool'},
                {'name': 'https_proxy', 'title': 'HTTPS Proxy', 'type': 'string'},
            ],
            'required': ['domain', 'username', 'password', *[x['name'] for x in FETCH_OPTS], 'verify_ssl', ],
            'type': 'array',
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {'name': 'trust_hostname', 'title': 'Trust Tanium Discover hostname', 'type': 'bool'},
                {'name': 'page_size', 'title': 'Number of assets to fetch per page', 'type': 'integer'},
                {
                    'name': 'page_sleep',
                    'title': 'Number of seconds to wait in between each page fetch',
                    'type': 'integer',
                },
            ],
            'required': ['trust_hostname', 'page_size', 'page_sleep'],
            'pretty_name': 'Tanium Discover Configuration',
            'type': 'array',
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'trust_hostname': False,
            'page_size': PAGE_SIZE,
            'page_sleep': PAGE_SLEEP,
        }

    def _on_config_update(self, config):
        self.__trust_hostname = config.get('trust_hostname') or False
        self._page_size = config.get('page_size', PAGE_SIZE)
        self._page_sleep = config.get('page_sleep', PAGE_SLEEP)
