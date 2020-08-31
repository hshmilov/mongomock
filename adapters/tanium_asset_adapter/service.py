import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter, get_settings_cached
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import figure_out_os
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.utils.files import get_local_config_file
from axonius.mixins.configurable import Configurable
from axonius.clients import tanium

from tanium_asset_adapter.connection import TaniumAssetConnection
from tanium_asset_adapter.consts import PAGE_SIZE

logger = logging.getLogger(f'axonius.{__name__}')


class LastUsedTime(SmartJsonClass):
    days_since_last_used = Field(field_type=int, title='Days Since Last Used')
    description = Field(field_type=str, title='Description')
    executable = Field(field_type=str, title='Executable')


class SqlServer(SmartJsonClass):
    display_name = Field(field_type=str, title='Display Name')
    instance_name = Field(field_type=str, title='Instance Name')
    product_level = Field(field_type=str, title='Product Level')
    server_edition = Field(field_type=str, title='Server Edition')
    product_version = Field(field_type=str, title='Product Version', json_format=JsonStringFormat.version)


class TaniumAssetAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        server_name = Field(field_type=str, title='Tanium Server')
        server_version = Field(field_type=str, title='Tanium Server Version', json_format=JsonStringFormat.version)
        module_version = Field(field_type=str, title='Module Version', json_format=JsonStringFormat.version)
        asset_id = Field(field_type=int, title='Asset ID')
        asset_os = Field(field_type=str, title='Asset OS')
        asset_os_platform = Field(field_type=str, title='Asset OS Platform')
        asset_os_sp = Field(field_type=str, title='Asset OS Service Pack')
        asset_os_version = Field(field_type=str, title='Asset OS Version')
        asset_user_name = Field(field_type=str, title='Asset User Name')
        asset_ip = Field(field_type=str, title='Asset IP Address', json_format=JsonStringFormat.ip)
        chassis_type = Field(field_type=str, title='Asset Chassis Type')
        city = Field(field_type=str, title='Asset City')
        computer_id = Field(field_type=int, title='Asset Computer ID')
        country = Field(field_type=str, title='Asset Country')
        created_at = Field(field_type=datetime.datetime, title='Asset Created At')
        department = Field(field_type=str, title='Asset Department')
        disk_total_space = Field(field_type=int, title='Asset Total Disk Space (GB)')
        display_adapter_count = Field(field_type=int, title='Asset Number of Display Adapters')
        last_seen_at = Field(field_type=datetime.datetime, title='Asset Last Seen At')
        number_of_fixed_drive = Field(field_type=int, title='Asset Number of Fixed Drives')
        number_of_logical_processor = Field(field_type=int, title='Asset Number of Logical Processors')
        phone_number = Field(field_type=str, title='Asset Phone Number')
        updated_at = Field(field_type=datetime.datetime, title='Asset Updated At')
        sql_server = ListField(field_type=SqlServer, title='SQL Server')
        application_last_used_time = ListField(field_type=LastUsedTime, title='Application Last Used Time')

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
        connection = TaniumAssetConnection(
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
                client_name=client_name, client_config=client_config, page_size=self.__page_size,
            )

    @staticmethod
    def _add_last_used_user(device, device_raw, key, attr):
        value = device_raw.get(key)
        src = {'value': value, 'key': key, 'attr': attr}
        value = tanium.tools.parse_str(value=value, src=src)
        if not tanium.tools.is_empty(value=value):
            device.last_used_users.append(value)

    @staticmethod
    def _figure_os(device, device_raw, key, attr):
        try:
            value = device_raw.get(key)
            src = {'value': value, 'key': key, 'attr': attr}
            value = tanium.tools.parse_str(value=value, src=src)
            if not tanium.tools.is_empty(value=value):
                device.figure_os(value)
        except Exception:
            logger.exception(f'ERROR in value {value!r}')

    @staticmethod
    def _set_os_type(device, device_raw, key, attr):
        tanium.tools.ensure_os(device=device)

        value = device_raw.get(key)
        src = {'value': value, 'key': key, 'attr': attr}

        value = tanium.tools.parse_str(value=value, src=src)
        value = figure_out_os(value)
        value = value.get('type')

        if not tanium.tools.is_empty(value=value) and not device.os.get_field_safe(attr=attr):
            setattr(device.os, attr, value)

    @staticmethod
    def _set_os_sp(device, device_raw, key, attr):
        tanium.tools.ensure_os(device=device)

        value = device_raw.get(key)
        src = {'value': value, 'key': key, 'attr': attr}

        value = tanium.tools.parse_str(value=value, src=src)

        if not tanium.tools.is_empty(value=value) and not device.os.get_field_safe(attr=attr):
            setattr(device.os, attr, value)

    @staticmethod
    def _set_os_build(device, device_raw, key, attr):
        tanium.tools.ensure_os(device=device)

        value = device_raw.get(key)
        src = {'value': value, 'key': key, 'attr': attr}

        value = tanium.tools.parse_str(value=value, src=src)

        if not tanium.tools.is_empty(value=value) and not device.os.get_field_safe(attr=attr):
            setattr(device.os, attr, value)

    @staticmethod
    def _set_uptime(device, device_raw, key, attr):
        value = device_raw.get(key)
        src = {'value': value, 'key': key, 'attr': attr}

        value = tanium.tools.parse_int(value=value, src=src)

        if isinstance(value, int):
            value = value / 1000 / 60 / 60 / 24
            value = tanium.tools.parse_int(value=value, src=src)
            if not tanium.tools.is_empty(value=value):
                device.uptime = value

                try:
                    device.boot_time = tanium.tools.dt_now(utc=True) - datetime.timedelta(days=value)
                except Exception:
                    device.boot_time = tanium.tools.dt_now(utc=False) - datetime.timedelta(days=value)

    @staticmethod
    def _add_cpu(device, device_raw, key, attr):
        name = device_raw.get('cpu_name')
        name_src = {'value': name, 'key': key, 'attr': attr}
        name = tanium.tools.parse_str(value=name, src=name_src)

        cores = device_raw.get('cpu_core')
        cores_src = {'value': cores, 'key': key, 'attr': attr}
        cores = tanium.tools.parse_int(value=cores, src=cores_src)

        manufacturer = device_raw.get('cpu_manufacturer')
        manufacturer_src = {'value': manufacturer, 'key': key, 'attr': attr}
        manufacturer = tanium.tools.parse_str(value=manufacturer, src=manufacturer_src)

        ghz = device_raw.get('cpu_speed')
        ghz_src = {'value': manufacturer, 'key': key, 'attr': attr}
        ghz = tanium.tools.parse_str(value=ghz, src=ghz_src)
        ghz = ''.join(x for x in ghz if x.isdigit()) if isinstance(ghz, str) else None
        ghz = tanium.tools.parse_int(value=ghz, src=ghz_src)
        ghz = (ghz / 1000 / 1000 / 1000) if isinstance(ghz, int) else None

        kwargs = dict(name=name, cores=cores, ghz=ghz, manufacturer=manufacturer)
        if not tanium.tools.is_empty_vals(value=kwargs):
            try:
                device.add_cpu(**kwargs)
            except Exception:
                logger.exception(f'ERROR appending with kwargs {kwargs!r}')

    @staticmethod
    def _add_nic(device, device_raw, key, attr):
        values = device_raw.get(key)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            src = {'value': value, 'key': key, 'attr': attr}

            ipv4 = value.get('ipv4_address')
            ipv4 = tanium.tools.parse_ip(value=ipv4, src=src)

            mask = value.get('subnet_mask')
            subnet = tanium.tools.parse_ip_network(ip=ipv4, mask=mask, src=src)
            subnets = tanium.tools.listify(value=subnet, clean=True)

            ipv6 = value.get('ipv6_address')
            ipv6 = tanium.tools.parse_ip(value=ipv6, src=src)

            ips = tanium.tools.listify(value=[ipv4, ipv6], clean=True)

            mac = value.get('mac_address')
            mac = tanium.tools.parse_mac(value=mac, src=src)

            gw = value.get('gateway')
            gw = tanium.tools.parse_ip(value=gw, src=src)

            name = value.get('name')
            name = tanium.tools.parse_str(value=name, src=src)

            kwargs = dict(ips=ips, mac=mac, subnets=subnets, gateway=gw, name=name)

            if not tanium.tools.is_empty_list(value=ips):
                try:
                    device.add_nic(**kwargs)
                except Exception:
                    logger.exception(f'ERROR appending with kwargs {kwargs!r}')

    @staticmethod
    def _add_sw(device, device_raw, key, attr):
        values = device_raw.get(key)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            src = {'value': value, 'key': key, 'attr': attr}
            name = value.get('name')
            name = tanium.tools.parse_str(value=name, src=src)

            vendor = value.get('vendor')
            vendor = tanium.tools.parse_str(value=vendor, src=src)

            norm_name = value.get('normalized_name')
            norm_name = tanium.tools.parse_str(value=norm_name, src=src)

            norm_vendor = value.get('normalized_vendor')
            norm_vendor = tanium.tools.parse_str(value=norm_vendor, src=src)

            version = value.get('version')
            version = tanium.tools.parse_str(value=version, src=src)

            kwargs = dict(name=norm_name or name, version=version, vendor=norm_vendor or vendor)
            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.add_installed_software(**kwargs)
                except Exception:
                    logger.exception(f'ERROR appending with kwargs {kwargs!r}')

    @staticmethod
    def _add_disks(device, device_raw, key, attr):
        values = device_raw.get(key)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            src = {'value': value, 'key': key, 'attr': attr}
            dvc = value.get('name')
            dvc = tanium.tools.parse_str(value=dvc, src=src)

            file_system = value.get('file_system')
            file_system = tanium.tools.parse_str(value=file_system, src=src)

            path = value.get('mount_point')
            path = tanium.tools.parse_str(value=path, src=src)

            total_size = value.get('size')
            total_size = tanium.tools.calc_gb(value=total_size, src=src)

            free_size = value.get('free_space')
            free_size = tanium.tools.calc_gb(value=free_size, src=src)

            description = value.get('media_type')
            description = tanium.tools.parse_str(value=description, src=src)

            kwargs = dict(
                path=path,
                device=dvc,
                file_system=file_system,
                total_size=total_size,
                free_size=free_size,
                description=description,
            )
            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.add_hd(**kwargs)
                except Exception:
                    logger.exception(f'ERROR appending with kwargs {kwargs!r}')

    @staticmethod
    def _add_sql(device, device_raw, key, attr):
        values = device_raw.get(key)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            src = {'value': value, 'key': key, 'attr': attr}

            sql_display_name = value.get('sql_display_name')
            sql_display_name = tanium.tools.parse_str(value=sql_display_name, src=src)

            sql_instance_name = value.get('sql_instance_name')
            sql_instance_name = tanium.tools.parse_str(value=sql_instance_name, src=src)

            sql_product_level = value.get('sql_product_level')
            sql_product_level = tanium.tools.parse_str(value=sql_product_level, src=src)

            sql_product_version = value.get('sql_product_version')
            sql_product_version = tanium.tools.parse_str(value=sql_product_version, src=src)

            sql_server_edition = value.get('sql_server_edition')
            sql_server_edition = tanium.tools.parse_str(value=sql_server_edition, src=src)

            kwargs = dict(
                display_name=sql_display_name,
                instance_name=sql_instance_name,
                product_level=sql_product_level,
                product_version=sql_product_version,
                server_edition=sql_server_edition,
            )
            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.sql_server.append(SqlServer(**kwargs))
                except Exception:
                    logger.exception(f'ERROR appending with kwargs {kwargs!r}')

    @staticmethod
    def _add_app_last_used(device, device_raw, key, attr):
        values = device_raw.get(key)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            src = {'value': value, 'key': key, 'attr': attr}

            days_since_last_used = value.get('days_since_last_used')
            days_since_last_used = tanium.tools.parse_int(value=days_since_last_used, src=src)

            description = value.get('description')
            description = tanium.tools.parse_str(value=description, src=src)

            executable = value.get('executable')
            executable = tanium.tools.parse_str(value=executable, src=src)

            kwargs = dict(days_since_last_used=days_since_last_used, description=description, executable=executable)
            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    if get_settings_cached()['should_populate_heavy_fields']:
                        device.application_last_used_time.append(LastUsedTime(**kwargs))
                except Exception:
                    logger.exception(f'ERROR appending with kwargs {kwargs!r}')

    @staticmethod
    def _add_patches(device, device_raw, key, attr):
        values = device_raw.get(key)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            src = {'value': value, 'key': key, 'attr': attr}

            msrc_severity = value.get('severity')
            msrc_severity = tanium.tools.parse_str(value=msrc_severity, src=src)

            title = value.get('title')
            title = tanium.tools.parse_str(value=title, src=src)

            security_bulletin_ids = value.get('cve_id')
            security_bulletin_ids = tanium.tools.parse_csv(value=security_bulletin_ids, split=' ', src=src)

            kb_article_ids = value.get('kb_article')
            kb_article_ids = tanium.tools.parse_csv(value=kb_article_ids, src=src)

            state = value.get('install_status')
            state = tanium.tools.parse_str(value=state, src=src)

            publish_date = value.get('release_date')
            publish_date = tanium.tools.parse_dt(value=publish_date, src=src)

            kwargs = dict(
                msrc_severity=msrc_severity,
                title=title,
                security_bulletin_ids=security_bulletin_ids,
                kb_article_ids=kb_article_ids,
                state=state,
                publish_date=publish_date,
            )
            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.add_available_security_patch(**kwargs)
                except Exception:
                    logger.exception(f'ERROR with kwargs {kwargs!r}')

    @staticmethod
    def _set_last_seen(device, device_raw, key, attr):
        updated_at = device_raw.get('updated_at')
        updated_at_src = {'value': updated_at, 'key': key, 'attr': attr}
        updated_at = tanium.tools.parse_dt(value=updated_at, src=updated_at_src)

        last_seen_at = device_raw.get('last_seen_at')
        last_seen_at_src = {'value': last_seen_at, 'key': key, 'attr': attr}
        last_seen_at = tanium.tools.parse_dt(value=last_seen_at, src=last_seen_at_src)

        pvalue = last_seen_at or updated_at
        device.last_seen = pvalue

    @staticmethod
    def _set_gb(device, device_raw, key, attr):
        value = device_raw.get(key)
        src = {'value': value, 'key': key, 'attr': attr}
        pvalue = tanium.tools.calc_gb(value=value, src=src)

        if not tanium.tools.is_empty(value=value):
            setattr(device, attr, pvalue)

    @property
    def key_attr_map(self):
        """Maps keys in device_raw to attributes to set on device adapter and method to use.

        (key in device_raw to get value from, attr to set value on device, method to use to set value on attr)
        """
        aggregated_firsts = [
            ('operating_system', None, self._figure_os),
        ]
        aggregated = [
            ('ci_applicable_patch', None, self._add_patches),
            ('ci_installed_application', None, self._add_sw),
            ('ci_logical_disk', None, self._add_disks),
            ('ci_network_adapter', None, self._add_nic),
            ('ci_windows_installer_application', None, self._add_sw),
            ('computer_name', 'hostname', tanium.tools.set_str),
            ('cpu_name', None, self._add_cpu),  # cpu_name, cpu_core, cpu_manufacturer, cpu_speed
            ('created_at', 'first_seen', tanium.tools.set_dt),
            ('domain_name', 'domain', tanium.tools.set_str),
            ('email', 'email', tanium.tools.set_str),
            (None, None, self._set_last_seen),  # last_seen_at, updated_at
            ('manufacturer', 'device_manufacturer', tanium.tools.set_str),
            ('model', 'device_model', tanium.tools.set_str),
            ('os_platform', 'type', self._set_os_type),
            ('os_version', 'build', self._set_os_build),
            ('ram', 'total_physical_memory', self._set_gb),
            ('serial_number', 'device_serial', tanium.tools.set_str),
            ('service_pack', 'sp', self._set_os_sp),
            ('system_uuid', 'uuid', tanium.tools.set_str),
            ('uptime', None, self._set_uptime),
            ('user_name', None, self._add_last_used_user),
            ('is_virtual', 'virtual_host', tanium.tools.set_bool),
        ]
        specific = [
            ('chassis_type', 'chassis_type', tanium.tools.set_str),
            ('ci_application_last_used_time', None, self._add_app_last_used),
            ('ci_sql_server', None, self._add_sql),
            ('city', 'city', tanium.tools.set_str),
            ('computer_id', 'computer_id', tanium.tools.set_int),
            ('country', 'country', tanium.tools.set_str),
            ('created_at', 'created_at', tanium.tools.set_dt),
            ('department', 'department', tanium.tools.set_str),
            ('disk_total_space', 'disk_total_space', self._set_gb),
            ('display_adapter_count', 'display_adapter_count', tanium.tools.set_int),
            ('id', 'asset_id', tanium.tools.set_int),
            ('ip_address', 'asset_ip', tanium.tools.set_ip),
            ('last_seen_at', 'last_seen_at', tanium.tools.set_dt),
            ('number_of_fixed_drive', 'number_of_fixed_drive', tanium.tools.set_int),
            ('number_of_logical_processor', 'number_of_logical_processor', tanium.tools.set_int),
            ('operating_system', 'asset_os', tanium.tools.set_str),
            ('os_platform', 'asset_os_platform', tanium.tools.set_str),
            ('os_version', 'asset_os_version', tanium.tools.set_str),
            ('phone_number', 'phone_number', tanium.tools.set_str),
            ('service_pack', 'asset_os_sp', tanium.tools.set_str),
            ('updated_at', 'updated_at', tanium.tools.set_dt),
            ('user_name', 'asset_user_name', tanium.tools.set_str),
        ]
        return aggregated_firsts + aggregated + specific

    def _create_device(self, device_raw, metadata):
        cid_key = 'computer_id'
        cid = device_raw.get(cid_key)
        cid = tanium.tools.parse_str(value=cid, src=cid_key)

        uuid_key = 'system_uuid'
        uuid = device_raw.get(uuid_key)
        uuid = tanium.tools.parse_str(value=uuid, src=uuid_key)

        serial_key = 'serial_number'
        serial = device_raw.get(serial_key)
        serial = tanium.tools.parse_str(value=serial, src=serial_key)

        asset_id_key = 'id'
        asset_id = device_raw.get(asset_id_key)
        asset_id = tanium.tools.parse_int(value=asset_id, src=asset_id_key)

        id_map = {cid_key: cid, uuid_key: uuid, serial_key: serial, asset_id_key: asset_id}
        if tanium.tools.is_empty_vals(value=id_map):
            logger.error(f'Bad device with no {list(id_map)} in {device_raw}')
            return None

        device = self._new_device_adapter()
        device.id = tanium.tools.joiner(cid, uuid, serial, asset_id, join='_')

        tanium.tools.set_module_ver(device=device, metadata=metadata, module='asset')
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
                # {'name': 'asset_dvc', 'type': 'string', 'title': 'Name of report to fetch', 'default': 'All Assets'},
                {'name': 'verify_ssl', 'title': 'Verify SSL', 'type': 'bool'},
                {'name': 'https_proxy', 'title': 'HTTPS Proxy', 'type': 'string'},
            ],
            'required': ['domain', 'username', 'password', 'verify_ssl', 'asset_dvc'],
            'type': 'array',
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'page_size',
                    'title': 'Number of assets to fetch per page',
                    'type': 'integer',
                    'default': PAGE_SIZE,

                },
            ],
            'required': [
                'page_size',
            ],
            'pretty_name': 'Tanium Asset Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'page_size': PAGE_SIZE,
        }

    def _on_config_update(self, config):
        self.__page_size = config.get('page_size') or PAGE_SIZE
