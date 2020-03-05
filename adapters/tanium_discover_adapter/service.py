import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients import tanium
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.utils.parsing import format_ip, figure_out_os
from axonius.utils.files import get_local_config_file
from tanium_discover_adapter.consts import METHODS

from tanium_discover_adapter.connection import TaniumDiscoverConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumDiscoverAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        server_name = Field(field_type=str, title='Tanium Server')
        server_version = Field(field_type=str, title='Tanium Server Version', json_format=JsonStringFormat.version)
        module_version = Field(field_type=str, title='Module Version', json_format=JsonStringFormat.version)
        tags_cloud = ListField(field_type=str, title='Tags Cloud')
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
        nat_ipaddress = Field(
            field_type=str, title='NAT IP Address', converter=format_ip, json_format=JsonStringFormat.ip
        )
        network_id = Field(field_type=str, title='Network ID')
        owner_id = Field(field_type=str, title='Owner ID')
        profile = Field(field_type=str, title='Profile')
        provider = Field(field_type=str, title='Provider')
        updated_at = Field(field_type=datetime.datetime, title='Updated At')
        zone = Field(field_type=str, title='Zone')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        # add all of the elements of the cnx to the client id to ensure uniqueness
        return client_config['domain'] + '_' + client_config['username']

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
            msg = f'Error connecting to client at {domain!r}, reason: {exc}'
            logger.exception(msg)
            raise ClientConnectionException(msg)

    def _query_devices_by_client(self, client_name, client_data):
        connection, client_config = client_data
        with connection:
            yield from connection.get_device_list(client_name=client_name, client_config=client_config)

    @staticmethod
    def _add_nic(device, device_raw, key, attr):
        ips = device_raw.get('ipaddress')
        mac = device_raw.get('macaddress')
        pips = tanium.tools.listify(tanium.tools.parse_ip(ips), clean=True)
        pmac = tanium.tools.parse_mac(mac)

        try:
            if pips:
                device.add_nic(mac=pmac, ips=pips)
        except Exception:
            logger.exception(f'Problem in add_nic ips {ips!r} mac {mac!r} in {device_raw!r}')

    @staticmethod
    def _add_adapter_tags(device, device_raw, key, attr):
        values = device_raw.get(key)
        pvalues = tanium.tools.parse_csv(values)

        for value in pvalues:
            try:
                device.add_key_value_tag(key=value, value=None)

            except Exception:
                logger.exception(f'Problem adding adapter tag {value!r} in {device_raw!r}')

    @staticmethod
    def _add_open_ports(device, device_raw, key, attr):
        values = device_raw.get(key)
        pvalues = tanium.tools.parse_csv(values)

        for value in pvalues:
            try:
                device.add_open_port(port_id=value)
            except Exception:
                logger.exception(f'Problem adding open port {value!r} in {device_raw!r}')

    @staticmethod
    def _figure_os(device, device_raw, key, attr):
        value = device_raw.get(key)
        os_type = figure_out_os(value).get('type')  # Linux
        tags = tanium.tools.parse_csv(device_raw.get('tags'))
        os_tags = tanium.tools.parse_empty([figure_out_os(x).get('type') for x in tags])  # Windows, Linux

        os_changes = [os_type]

        for os_tag in os_tags:
            if os_tag not in os_changes:
                os_type = os_tag
                os_changes.append(os_tag)

        if os_type:
            try:
                device.figure_os(os_type)
            except Exception:
                logger.exception(f'Problem in os_type {os_type!r} value {value!r} in {device_raw!r}')

            try:
                device.os.is_windows_server = None
            except Exception:
                logger.exception(f'Problem wiping out is_windows_server in {device_raw!r}')

    @staticmethod
    def _set_methods(device, device_raw, key, attr):
        value = device_raw.get(key)
        methods = tanium.tools.parse_csv(value)

        try:
            methods_used = dict(zip(METHODS, methods))
            for method, enabled in methods_used.items():
                if str(enabled).strip() == '1':
                    device.methods_used.append(method)
        except Exception:
            logger.exception(f'Problem in _set_methods {value!r} in {device_raw!r}')

    @property
    def _attr_map(self):
        return [
            # device_raw key, device attr, , set method
            ('cloudTags', 'tags_cloud', tanium.tools.set_csv),
            ('cloudTags', None, self._add_adapter_tags),
            ('computerid', 'computer_id', tanium.tools.set_str),
            ('computerid', 'uuid', tanium.tools.set_str),
            ('createdAt', 'created_at', tanium.tools.set_dt),
            ('createdAt', 'first_seen', tanium.tools.set_dt),
            ('hostname', 'hostname', tanium.tools.set_str),
            ('ignored', 'is_ignored', tanium.tools.set_bool),
            ('instanceId', 'instance_id', tanium.tools.set_str),
            ('instanceState', 'instance_state', tanium.tools.set_str),
            ('instanceType', 'instance_type', tanium.tools.set_str),
            ('ipaddress', None, self._add_nic),
            ('ismanaged', 'is_managed', tanium.tools.set_bool),
            ('lastDiscoveredAt', 'last_discovered_at', tanium.tools.set_dt),
            ('lastDiscoveredAt', 'last_seen', tanium.tools.set_dt),
            ('lastManagedAt', 'last_managed_at', tanium.tools.set_dt),
            ('launchTime', 'launch_time', tanium.tools.set_dt),
            ('locations', 'locations', tanium.tools.set_csv),
            ('method', None, self._set_methods),
            ('macorganization', 'mac_organization', tanium.tools.set_str),
            ('natipaddress', 'nat_ipaddress', tanium.tools.set_ip),
            ('networkId', 'network_id', tanium.tools.set_str),
            ('os', 'os_scanned', tanium.tools.set_str),
            ('os', None, self._figure_os),
            ('osgeneration', 'os_generation', tanium.tools.set_str),
            ('ownerId', 'owner_id', tanium.tools.set_str),
            ('ports', None, self._add_open_ports),
            ('profile', 'profile', tanium.tools.set_csv),
            ('provider', 'provider', tanium.tools.set_str),
            ('tags', 'tags_discover', tanium.tools.set_csv),
            ('tags', None, self._add_adapter_tags),
            ('unmanageable', 'is_unmanageable', tanium.tools.set_bool),
            ('updatedAt', 'updated_at', tanium.tools.set_dt),
            ('zone', 'zone', tanium.tools.set_str),
        ]

    def _create_device(self, device_raw, metadata):
        device = self._new_device_adapter()

        mac = device_raw.get('macaddress')
        cid = str(device_raw.get('computerid'))

        if not any([mac, cid]):
            logger.error(f'Bad device with empty mac {mac!r} or cid {cid!r} in {device_raw}')
            return None

        dvc_id = '_'.join([mac, cid])

        device.id = dvc_id

        tanium.tools.set_module_ver(device=device, metadata=metadata, module='discover')
        tanium.tools.set_metadata(device=device, metadata=metadata)

        for key, attr, method in self._attr_map:
            try:
                method(device=device, device_raw=device_raw, key=key, attr=attr)
            except Exception:
                logger.exception(f'Problem in key {key!r} attr {attr!r} method {method!r} in {device_raw!r}')

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
                {'name': 'verify_ssl', 'title': 'Verify SSL', 'type': 'bool'},
                {'name': 'https_proxy', 'title': 'HTTPS Proxy', 'type': 'string'},
            ],
            'required': ['domain', 'username', 'password', 'verify_ssl'],
            'type': 'array',
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
