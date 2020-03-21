import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import figure_out_os
from axonius.fields import Field, JsonStringFormat
from axonius.utils.files import get_local_config_file

from axonius.clients.tanium import tools

from tanium_asset_adapter.connection import TaniumAssetConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumAssetAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        server_name = Field(field_type=str, title='Tanium Server')
        server_version = Field(field_type=str, title='Tanium Server Version', json_format=JsonStringFormat.version)
        module_version = Field(field_type=str, title='Module Version', json_format=JsonStringFormat.version)
        report_created_at = Field(field_type=datetime.datetime, title='Report Created At')
        report_updated_at = Field(field_type=datetime.datetime, title='Report Updated At')
        report_name = Field(field_type=str, title='Report Name')
        report_description = Field(field_type=str, title='Report Description')
        report_category = Field(field_type=str, title='Report Category')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        # add all of the elements of the cnx to the client id to ensure uniqueness
        domain = client_config['domain']
        username = client_config.get('username')
        asset_dvc = client_config.get('asset_dvc')

        return f'{domain}_{username}_{asset_dvc}'

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
            msg = f'Error connecting to client at {domain!r}, reason: {exc}'
            logger.exception(msg)
            raise ClientConnectionException(msg)

    def _query_devices_by_client(self, client_name, client_data):
        connection, client_config = client_data
        with connection:
            yield from connection.get_device_list(client_name=client_name, client_config=client_config)

    @staticmethod
    def _set_user(device, device_raw):
        users = tools.listify(tools.parse_str(device_raw.get('user_name')), clean=True)
        try:
            device.last_used_users.extend(users)
        except Exception:
            logger.exception(f'Problem adding last_used_users {users!r} in {device_raw!r}')

    @staticmethod
    def _figure_os(device, device_raw):
        os = tools.parse_str(device_raw.get('operating_system'))
        try:
            device.figure_os(os)
        except Exception:
            logger.exception(f'Problem in figure_os {os!r} in {device_raw!r}')

        os_type = tools.parse_str(device_raw.get('os_platform'))
        if os_type:
            try:
                os_type = figure_out_os(os_type).get('type')
                if tools.check_attr(device.os, 'platform') is None and os_type:
                    device.os.type = os_type
            except Exception:
                logger.exception(f'Problem adding os.type {os_type!r} in {device_raw!r}')

        os_sp = tools.parse_str(device_raw.get('service_pack'))
        try:
            if tools.check_attr(device.os, 'sp') is None and os_sp:
                device.os.sp = os_sp
        except Exception:
            logger.exception(f'Problem adding os.sp {os_sp!r} in {device_raw!r}')

        os_build = tools.parse_str(device_raw.get('os_version'))
        try:
            if tools.check_attr(device.os, 'build') is None and os_build:
                device.os.build = os_build
        except Exception:
            logger.exception(f'Problem adding os.build {os_build!r} in {device_raw!r}')

    def _set_ram(self, device, device_raw):
        ram = self._calc_gb(device_raw.get('ram'))

        if ram is not None:
            try:
                device.total_physical_memory = ram
            except Exception:
                logger.exception(f'Problem setting ram {ram!r} in {device_raw!r}')

    @staticmethod
    def _calc_gb(value):
        value = tools.parse_int(value)
        if value is not None:
            try:
                return value / (1024 ** 3)
            except Exception:
                logger.exception(f'unable to convert bytes {value!r} to gb')
        return None

    @staticmethod
    def _set_uptime(device, device_raw):
        uptime = tools.parse_int(device_raw.get('uptime'))
        uptime = tools.parse_int(uptime / 1000 / 60 / 60 / 24)

        if uptime is not None:
            try:
                device.uptime = uptime

                try:
                    device.boot_time = tools.dt_now(utc=True) - datetime.timedelta(days=uptime)
                except Exception:
                    device.boot_time = tools.dt_now(utc=False) - datetime.timedelta(days=uptime)

            except Exception:
                logger.exception(f'Problem setting uptime {uptime!r} in {device_raw!r}')

    @staticmethod
    def _add_cpu(device, device_raw):
        name = tools.parse_str(device_raw.get('cpu_name'))
        cores = tools.parse_int(device_raw.get('cpu_core'))
        manufacturer = tools.parse_str(device_raw.get('cpu_manufacturer'))
        ghz = None
        try:
            ghz = tools.parse_int(tools.parse_str(device_raw.get('cpu_speed')).replace('ghz', ''))
        except Exception:
            pass

        try:
            ghz = None if ghz is None else (ghz / 1000 / 1000 / 1000)
        except Exception:
            msg = f'unable to convert {ghz!r} to ghz'
            logger.exception(msg)
            ghz = None

        cpu = dict(name=name, cores=cores, ghz=ghz, manufacturer=manufacturer)
        if any(list(cpu.values())):
            try:
                device.add_cpu(**cpu)
            except Exception:
                logger.exception(f'Problem adding cpu {cpu!r} in {device_raw!r}')

    @staticmethod
    def _add_nic(device, device_raw):
        adapters = tools.listify(device_raw.get('ci_network_adapter'), clean=True)
        found_ips = []

        for adapter in adapters:
            subnets = tools.listify(tools.parse_ip_network(adapter.get('subnet_mask')), clean=True)
            ips = tools.listify(tools.parse_ip(adapter.get('ipv4_address')), clean=True)
            found_ips += [x for x in ips if x not in found_ips]
            mac = tools.parse_mac(adapter.get('mac_address'))
            gw = tools.parse_ip(adapter.get('gateway'))
            name = tools.parse_str(adapter.get('name'))
            nic = dict(ips=ips, mac=mac, subnets=subnets, gateway=gw, name=name)
            if any([ips, mac]):
                try:
                    device.add_nic(**nic)
                except Exception:
                    logger.exception(f'Problem adding nic {nic!r} in {device_raw!r}')

        ips = tools.listify(tools.parse_ip(device_raw.get('ip_address')), clean=True)
        ips = [x for x in ips if x not in found_ips]
        if ips:
            try:
                device.add_nic(ips=ips)
            except Exception:
                logger.exception(f'Problem adding ips {ips!r} in {device_raw!r}')

    @staticmethod
    def _add_sw(device, device_raw, apps):
        for app in apps:
            name = tools.parse_str(app.get('name'))
            vendor = tools.parse_str(app.get('vendor'))
            norm_name = tools.parse_str(app.get('normalized_name'))
            norm_vendor = tools.parse_str(app.get('normalized_vendor'))
            version = tools.parse_str(app.get('version'))

            sw = dict(name=norm_name or name, version=version, vendor=norm_vendor or vendor)
            if any(list(sw.values())):
                try:
                    device.add_installed_software(**sw)
                except Exception:
                    logger.exception(f'Problem adding sw {sw!r} in {device_raw!r}')

    def _add_apps(self, device, device_raw):
        apps = tools.listify(device_raw.get('ci_installed_application'), clean=True)
        self._add_sw(device=device, device_raw=device_raw, apps=apps)

    def _add_win_apps(self, device, device_raw):
        apps = tools.listify(device_raw.get('ci_windows_installer_application'), clean=True)
        self._add_sw(device=device, device_raw=device_raw, apps=apps)

    def _add_disks(self, device, device_raw):
        disks = tools.listify(device_raw.get('ci_logical_disk'), clean=True)
        for disk in disks:
            dvc = tools.parse_str(disk.get('name'))
            file_system = tools.parse_str(disk.get('file_system'))
            path = tools.parse_str(disk.get('mount_point'))
            total_size = self._calc_gb(disk.get('size'))
            free_size = self._calc_gb(disk.get('free_space'))
            description = tools.parse_str(disk.get('media_type'))

            dsk = dict(
                path=path,
                device=dvc,
                file_system=file_system,
                total_size=total_size,
                free_size=free_size,
                description=description,
            )
            if any(list(dsk.values())):
                try:
                    device.add_hd(**dsk)
                except Exception:
                    logger.exception(f'Problem adding dsk {dsk!r} in {device_raw!r}')

    def _create_device(self, device_raw, metadata):
        report = metadata['report']

        cid = device_raw.get('computer_id')
        uuid = device_raw.get('system_uuid')
        use_id = cid or uuid
        report_info = report.get('data', {}).get('report', {})
        report_name = report_info.get('reportName')

        if not any([cid, uuid]):
            logger.error(f'Bad device with no cid {cid!r} or uuid {uuid!r} in {device_raw}')
            return None

        device = self._new_device_adapter()
        device.id = f'ASSET_DEVICE_{report_name}_{use_id}'
        device.uuid = f'{use_id}'

        if not cid:
            device.adapter_properties = [AdapterProperty.Network]

        tools.set_module_ver(device=device, metadata=metadata, module='asset')
        tools.set_metadata(device=device, metadata=metadata)

        created_at = tools.parse_dt(report_info.get('createdAt'))
        updated_at = tools.parse_dt(report_info.get('updatedAt'))
        device.report_description = report_info.get('description')
        device.report_category = report_info.get('categoryName')
        device.report_created_at = created_at
        device.report_updated_at = updated_at
        device.first_seen = created_at
        device.last_seen = updated_at

        device.hostname = tools.parse_str(device_raw.get('computer_name'))
        device.device_serial = tools.parse_str(device_raw.get('serial_number'))
        device.device_manufacturer = tools.parse_str(device_raw.get('manufacturer'))
        device.device_model = tools.parse_str(device_raw.get('model'))
        device.domain = tools.parse_str(device_raw.get('domain_name'))

        methods = [
            self._set_user,
            self._figure_os,
            self._add_nic,
            self._set_ram,
            self._set_uptime,
            self._add_cpu,
            self._add_apps,
            self._add_win_apps,
            self._add_disks,
        ]
        for method in methods:
            try:
                method(device=device, device_raw=device_raw)
            except Exception:
                logger.exception(f'Problem in {method!r} in {device_raw!r}')

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
                {'name': 'asset_dvc', 'type': 'string', 'title': 'Name of report to fetch', 'default': 'All Assets'},
                {'name': 'verify_ssl', 'title': 'Verify SSL', 'type': 'bool'},
                {'name': 'https_proxy', 'title': 'HTTPS Proxy', 'type': 'string'},
            ],
            'required': ['domain', 'username', 'password', 'verify_ssl', 'asset_dvc'],
            'type': 'array',
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
