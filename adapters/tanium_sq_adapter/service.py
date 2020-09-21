import datetime
import json
import logging
import pathlib
import re

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients import tanium
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.consts.instance_control_consts import UPLOAD_FILE_PATH
from axonius.devices.device_adapter import AGENT_NAMES, DeviceAdapter, DeviceAdapterCPU, DeviceAdapterOS
from axonius.fields import Field, JsonStringFormat, ListField
from axonius.mixins.configurable import Configurable
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import normalize_var_name
from tanium_sq_adapter.connection import TaniumSqConnection
from tanium_sq_adapter.consts import (
    IPV4_SENSOR,
    MAC_SENSOR,
    MAX_HOURS,
    NET_SENSOR_DISCOVER,
    NET_SENSORS,
    NO_RESULTS_WAIT,
    PAGE_SIZE,
    REFRESH,
    SLEEP_GET_ANSWERS,
)


logger = logging.getLogger(f'axonius.{__name__}')
# pylint: disable=too-many-locals,C0330,too-many-lines


def new_complex():
    class ComplexSensor(SmartJsonClass):
        pass

    return ComplexSensor


class ComplianceAggregates(SmartJsonClass):
    engine = Field(field_type=str, title='Engine')
    hash_value = Field(field_type=str, title='Hash')
    error_code = Field(field_type=str, title='Error Code')
    version = Field(field_type=str, title='Version')

    count_all = Field(field_type=int, title='All Count')

    count_pass = Field(field_type=int, title='Pass Count')
    count_fail = Field(field_type=int, title='Fail Count')
    count_error = Field(field_type=int, title='Error Count')
    count_unknown = Field(field_type=int, title='Unknown Count')
    count_not_applicable = Field(field_type=int, title='Not Applicable Count')
    count_not_checked = Field(field_type=int, title='Not Checked Count')
    count_not_selected = Field(field_type=int, title='Not Selected Count')
    count_informational = Field(field_type=int, title='Informational Count')
    count_fixed = Field(field_type=int, title='Fixed Count')

    percent_pass = Field(field_type=float, title='Pass Percent')
    percent_fail = Field(field_type=float, title='Fail Percent')
    percent_error = Field(field_type=float, title='Error Percent')
    percent_unknown = Field(field_type=float, title='Unknown Percent')
    percent_not_applicable = Field(field_type=float, title='Not Applicable Percent')
    percent_not_checked = Field(field_type=float, title='Not Checked Percent')
    percent_not_selected = Field(field_type=float, title='Not Selected Percent')
    percent_informational = Field(field_type=float, title='Informational Percent')
    percent_fixed = Field(field_type=float, title='Fixed Percent')


class VulnerabilityAggregates(SmartJsonClass):
    engine = Field(field_type=str, title='Engine')
    hash_value = Field(field_type=str, title='Hash')
    error_code = Field(field_type=str, title='Error Code')

    count_all = Field(field_type=int, title='All Count')

    count_vulnerable = Field(field_type=int, title='Vulnerable Count')
    count_non_vulnerable = Field(field_type=int, title='Non Vulnerable Count')
    count_error = Field(field_type=int, title='Error Count')
    count_high_severity = Field(field_type=int, title='High Severity Count')
    count_medium_severity = Field(field_type=int, title='Medium Severity Count')
    count_low_severity = Field(field_type=int, title='Low Severity Count')

    percent_vulnerable = Field(field_type=float, title='Vulnerable Percent')
    percent_non_vulnerable = Field(field_type=float, title='Non Vulnerable Percent')
    percent_error = Field(field_type=float, title='Error Percent')
    percent_high_severity = Field(field_type=float, title='High Severity Percent')
    percent_medium_severity = Field(field_type=float, title='Medium Severity Percent')
    percent_low_severity = Field(field_type=float, title='Low Severity Percent')


class TaniumSqAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        server_name = Field(field_type=str, title='Tanium Server')
        server_version = Field(field_type=str, title='Tanium Server Version', json_format=JsonStringFormat.version)
        module_version = Field(field_type=str, title='Module Version', json_format=JsonStringFormat.version)
        sq_name = Field(field_type=str, title='Saved Question Name')
        sq_query_text = Field(field_type=str, title='Question Query Text')
        sq_expiration = Field(field_type=datetime.datetime, title='Question Last Asked')
        sq_selects = ListField(field_type=str, title='Question Selects')
        compliance = ListField(field_type=ComplianceAggregates, title='Compliance')
        vulnerabilities = ListField(field_type=VulnerabilityAggregates, title='Vulnerabilities')

    def __init__(self, *args, **kwargs):
        self._page_size = PAGE_SIZE
        self._page_sleep = SLEEP_GET_ANSWERS
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return tanium.tools.joiner(
            client_config['domain'], client_config['username'], client_config['sq_name'], join='_',
        )

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(
            client_config.get('domain'), https_proxy=client_config.get('https_proxy')
        )

    @staticmethod
    def get_connection(client_config):
        domain = client_config['domain']
        file_pre = 'file://'
        file_ext = '.json'
        if domain.startswith(file_pre):
            # look for it in /home/cortex, if not found throw error
            # if found json.load() yield each item to the thing
            file_path = pathlib.Path(domain)
            if file_path.suffix != file_ext:
                raise RESTException(f'File name does not end with {file_ext!r}: {file_path.name}')
            # how to find file in /home/ubuntu/cortex or /home/ubuntu/cortex/adapters/tanium_sq_adapter/
            upload_file_path = pathlib.Path(UPLOAD_FILE_PATH) / file_path.name
            actual_path = pathlib.Path('/home/ubuntu/cortex/uploaded_files') / file_path.name
            if not upload_file_path.is_file():
                raise RESTException(f'File not found: {actual_path}')
            return upload_file_path

        connection = TaniumSqConnection(
            domain=domain,
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
            return self.get_connection(client_config=client_config), client_config
        except RESTException as exc:
            raise ClientConnectionException(f'Error connecting to client at {domain!r}, reason: {exc}')

    def _query_devices_by_client(self, client_name, client_data):
        connection, client_config = client_data

        if isinstance(connection, pathlib.Path):
            with connection.open('r') as fh:
                assets = json.load(fh)
                yield from assets
        else:
            with connection:
                yield from connection.get_device_list(
                    client_name=client_name,
                    client_config=client_config,
                    page_size=self._page_size,
                    page_sleep=self._page_sleep,
                )

    def _sens_hostname(self, device, name, value_map):
        """Sensor: Computer Name."""
        value = self._get_value(name=name, value_map=value_map, first=True)

        if not tanium.tools.is_empty(value=value):
            try:
                if value:
                    if value.endswith('.(none)'):
                        value = value[: -len('.(none)')]
                    if './bin/sh' in value:
                        value = value[: value.find('./bin/sh')]
            except Exception:
                logger.exception(f'ERROR getting host_name from')
            device.hostname = value

    def _sens_serial(self, device, name, value_map):
        """Sensor: Computer Serial Number."""
        value = self._get_value(name=name, value_map=value_map, first=True)

        if not tanium.tools.is_empty(value=value):
            device.device_serial = value

    def _sens_instapps(self, device, name, value_map):
        """Sensor: Installed Applications."""
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            name = self._get_valuedata(name=name, key='Name', value=value)
            version = self._get_valuedata(name=name, key='Version', value=value)

            kwargs = dict(name=name, version=version)

            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.add_installed_software(**kwargs)
                except Exception:
                    logger.exception(f'ERROR in name {name!r} value {value!r} kwargs {kwargs}')

    def _sens_chassis(self, device, name, value_map):
        """Sensor: Chassis Type."""
        value = self._get_value(name=name, value_map=value_map, first=True)

        if not tanium.tools.is_empty(value=value):
            if 'virtual' in str(value).lower() and device.get_field_safe(attr='virtual_host') is None:
                device.virtual_host = True

    def _sens_lastuser(self, device, name, value_map):
        """Sensor: Last Logged In User."""
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            try:
                if value not in device.last_used_users:
                    device.last_used_users.append(value)
            except Exception:
                logger.exception(f'ERROR in name {name!r} value_map {value_map!r} value {value!r}')

    def _sens_lastreboot(self, device, name, value_map):
        """Sensor: Last Reboot."""
        src = {'name': name, 'value_map': value_map}
        value = self._get_value(name=name, value_map=value_map, first=True)
        value = tanium.tools.parse_dt(value=value, src=src)

        if not tanium.tools.is_empty(value=value):
            if device.get_field_safe(attr='boot_time') is None:
                device.boot_time = value

            if device.get_field_safe(attr='uptime') is None:
                try:
                    device.uptime = (tanium.tools.dt_now(utc=True) - value).days
                except Exception:
                    device.uptime = (tanium.tools.dt_now(utc=False) - value).days

    def _sens_model(self, device, name, value_map):
        """Sensor: Model."""
        value = self._get_value(name=name, value_map=value_map, first=True)

        if not tanium.tools.is_empty(value=value):
            device.device_model = value

    def _sens_manufacturer(self, device, name, value_map):
        """Sensor: Manufacturer."""
        value = self._get_value(name=name, value_map=value_map, first=True)

        if not tanium.tools.is_empty(value=value):
            device.device_manufacturer = value

    def _sens_tags(self, device, name, value_map):
        """Sensor: Custom Tags."""
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            try:
                device.add_key_value_tag(key=value, value=None)
            except Exception:
                logger.exception(f'ERROR in name {name!r} value_map {value_map!r} value {value!r}')

    def _sens_openports(self, device, name, value_map):
        """Sensor: Open Ports."""
        src = {'name': name, 'value_map': value_map}
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)
        values = tanium.tools.parse_int(value=values, src=src)
        open_ports = [x.get_field_safe(attr='port_id') for x in device.open_ports]
        values = [x for x in values if x not in open_ports]

        for value in values:
            try:
                device.add_open_port(port_id=value)
            except Exception:
                logger.exception(f'ERROR in name {name!r} value_map {value_map!r} value {value!r}')

    @staticmethod
    def _get_enum_regex_match(adapter_cls, field, value):
        """Find a value that regex matches a fields enum value."""
        try:
            obj = adapter_cls()
            field_obj = obj.get_field_type(field)

            for enum_value in field_obj.enum:
                if re.search(str(enum_value), str(value), re.I):
                    return enum_value
        except Exception:
            return None
        return None

    def _sens_cpudetails(self, device, name, value_map):
        """Sensor: CPU Details."""
        src = {'name': name, 'value_map': value_map}
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            arch_value = self._get_valuedata(name=name, key='System Type', value=value)

            arch = self._get_enum_regex_match(adapter_cls=DeviceAdapterCPU, field='architecture', value=arch_value)
            bitness = self._get_enum_regex_match(adapter_cls=DeviceAdapterCPU, field='bitness', value=arch_value)

            # AX-7316
            # if '64' in str(arch):
            #     bitness = 64
            #     arch = 'x64'
            # elif 'x86' in str(arch):
            #     bitness = 32
            #     arch = 'x86'
            # else:
            #     try:
            #         valids = DeviceAdapterCPU.bitness.enum
            #         matches = [x for x in [re.search(v, arch) for v in valids] if x]
            #     except Exception:
            #         matches = []
            #     arch = matches[0] if matches else None
            #     bitness = None

            cpu = self._get_valuedata(name=name, key='CPU', value=value)

            ghz = self._get_valuedata(name=name, key='CPU Speed', value=value)
            ghz = str(ghz).lower().replace('mhz', '').strip()
            ghz = tanium.tools.parse_int(value=ghz, src=src)
            if ghz is not None:
                ghz = ghz / 1000

            cores = self._get_valuedata(name=name, key='Total Cores', value=value)
            cores = tanium.tools.parse_int(value=cores, src=src)

            kwargs = dict(name=cpu, bitness=bitness, cores=cores, architecture=arch, ghz=ghz)
            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.add_cpu(**kwargs)
                except Exception:
                    logger.exception(f'ERROR in name {name!r} value {value!r} kwargs {kwargs!r}')

    def _sens_netadapters(self, device, name, value_map):
        """Sensor: Network Adapters."""
        src = {'name': name, 'value_map': value_map}
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            ips = self._get_valuedata(name=name, key='IP Address', value=value)
            ips = tanium.tools.parse_csv(value=ips, src=src)
            ips = tanium.tools.parse_ip(value=ips, src=src)

            mac = self._get_valuedata(name=name, key='MAC Address', value=value)
            mac = tanium.tools.parse_mac(value=mac, src=src)

            kwargs = dict(ips=ips, mac=mac)
            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.add_nic(**kwargs)
                except Exception:
                    logger.exception(f'ERROR in name {name!r} value {value!r} kwargs {kwargs!r}')

    @staticmethod
    def _sens_ipmac(device, device_raw):
        """Network sensors: IPv4 Address and MAC Address."""
        ips = device_raw[IPV4_SENSOR]['value']
        ips = tanium.tools.listify(value=ips, clean=True)
        macs = device_raw[MAC_SENSOR]['value']
        macs = tanium.tools.listify(value=macs, clean=True)
        only_one_each = all([len(x) == 1 for x in [ips, macs]])

        # there is only one IP and one MAC, so we can safely assume they are related
        if only_one_each:
            kwargs = dict(ips=ips, mac=macs[0])
            try:
                device.add_nic(**kwargs)
            except Exception:
                logger.exception(f'ERROR in single IP/MAC with kwargs {kwargs!r}')
        # there is more than IP or MAC, so we have no idea how they are related
        # we will just add each IP and MAC individually as their own NIC
        else:
            for ip in ips:
                kwargs = dict(ips=[ip])
                try:
                    device.add_nic(**kwargs)
                except Exception:
                    logger.exception(f'ERROR in multi IP/MAC with kwargs {kwargs!r}')
            for mac in macs:
                kwargs = dict(mac=mac)
                try:
                    device.add_nic(**kwargs)
                except Exception:
                    logger.exception(f'ERROR in multi IP/MAC with kwargs {kwargs!r}')

    def _sens_opsys(self, device, name, value_map):
        """Sensor: Operating System."""
        value = self._get_value(name=name, value_map=value_map, first=True)
        if not tanium.tools.is_empty(value=value):
            device.figure_os(value)

    def _sens_services(self, device, name, value_map):
        """Sensor: Service Details."""
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            dname = self._get_valuedata(name=name, key='Service Display Name', value=value)
            status = self._get_valuedata(name=name, key='Service Status', value=value)
            name = self._get_valuedata(name=name, key='Service Name', value=value)

            kwargs = dict(name=name, display_name=dname, status=status)
            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.add_service(**kwargs)
                except Exception:
                    logger.exception(f'ERROR in name {name!r} value {value!r} kwargs {kwargs!r}')

    def _sens_service_pack(self, device, name, value_map):
        """Sensor: Service Pack."""
        value = self._get_value(name=name, value_map=value_map, first=True)

        if not tanium.tools.is_empty(value=value) and device.os.get_field_safe(attr='sp') is None:
            device.os.sp = value

    def _sens_memory(self, device, name, value_map):
        """Sensors: RAM, Total Memory."""
        src = {'name': name, 'value_map': value_map}
        value = self._get_value(name=name, value_map=value_map, first=True)
        value = str(value).lower().replace('mb', '').strip()
        value = tanium.tools.parse_int(value=value, src=src)
        if not tanium.tools.is_empty(value=value):
            device.total_physical_memory = value / 1024

    def _sens_uptime(self, device, name, value_map):
        """Sensor: Uptime."""
        src = {'name': name, 'value_map': value_map}
        value = self._get_value(name=name, value_map=value_map, first=True)
        value = str(value).lower().replace('days', '').strip()
        value = tanium.tools.parse_int(value=value, src=src)

        if not tanium.tools.is_empty(value=value):
            if device.get_field_safe(attr='boot_time') is None:
                try:
                    device.boot_time = tanium.tools.dt_now(utc=True) - datetime.timedelta(days=value)
                except Exception:
                    device.boot_time = tanium.tools.dt_now(utc=False) - datetime.timedelta(days=value)

            if device.get_field_safe(attr='uptime') is None:
                device.uptime = value

    def _sens_osplat(self, device, name, value_map):
        """Sensor: OS Platform."""
        value = self._get_value(name=name, value_map=value_map, first=True)

        if not tanium.tools.is_empty(value=value) and device.os.get_field_safe(attr='type') is None:
            device.os.type = value

    def _sens_osinstalldt(self, device, name, value_map):
        """Sensor: Operating System Install Date."""
        src = {'name': name, 'value_map': value_map}
        value = self._get_value(name=name, value_map=value_map, first=True)
        value = tanium.tools.parse_dt(value=value, src=src)

        if not tanium.tools.is_empty(value=value) and device.os.get_field_safe(attr='install_date') is None:
            device.os.install_date = value

    def _sens_osbuildnum(self, device, name, value_map):
        """Sensor: Operating System Build Number."""
        value = self._get_value(name=name, value_map=value_map, first=True)

        if not tanium.tools.is_empty(value=value) and device.os.get_field_safe(attr='build') is None:
            device.os.build = value

    def _sens_loggedin(self, device, name, value_map):
        """Sensor: Logged In Users."""
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            try:
                if device.get_field_safe(attr='current_logged_user') is None:
                    device.current_logged_user = value

                if value not in device.last_used_users:
                    device.last_used_users.append(value)
            except Exception:
                logger.exception(f'ERROR in name {name!r} value_map {value_map!r} value {value!r}')

    def _sens_domainmember(self, device, name, value_map):
        """Sensor: Domain Member."""
        src = {'name': name, 'value_map': value_map}
        value = self._get_value(name=name, value_map=value_map, first=True)
        value = tanium.tools.parse_bool(value=value, src=src)
        if not tanium.tools.is_empty(value=value):
            device.part_of_domain = value

    def _sens_timezone(self, device, name, value_map):
        """Sensor: Time Zone."""
        value = self._get_value(name=name, value_map=value_map, first=True)
        if not tanium.tools.is_empty(value=value):
            device.time_zone = value

    def _sens_biosver(self, device, name, value_map):
        """Sensor: BIOS Version."""
        value = self._get_value(name=name, value_map=value_map, first=True)
        if not tanium.tools.is_empty(value=value):
            device.bios_version = value

    def _sens_isvirt(self, device, name, value_map):
        """Sensor: Is Virtual."""
        src = {'name': name, 'value_map': value_map}
        value = self._get_value(name=name, value_map=value_map, first=True)
        value = tanium.tools.parse_bool(value=value, src=src)

        if not tanium.tools.is_empty(value=value) and device.os.get_field_safe(attr='virtual_host') is None:
            device.virtual_host = value

    def _sens_mobomanu(self, device, name, value_map):
        """Sensor: Motherboard Manufacturer."""
        value = self._get_value(name=name, value_map=value_map, first=True)
        if not tanium.tools.is_empty(value=value):
            device.motherboard_manufacturer = value

    def _sens_mobover(self, device, name, value_map):
        """Sensor: Motherboard Version."""
        value = self._get_value(name=name, value_map=value_map, first=True)
        if not tanium.tools.is_empty(value=value):
            device.motherboard_version = value

    def _sens_adorgunit(self, device, name, value_map):
        """Sensor: AD Organizational Unit."""
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            try:
                if value not in device.organizational_unit:
                    device.organizational_unit.append(value)
            except Exception:
                logger.exception(f'ERROR in name {name!r} value_map {value_map!r} value {value!r}')

    def _sens_openshares(self, device, name, value_map):
        """Sensor: Open Share Details."""
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            name = self._get_valuedata(name=name, key='Name', value=value)
            description = self._get_valuedata(name=name, key='Type', value=value)
            path = self._get_valuedata(name=name, key='Path', value=value)

            kwargs = dict(name=name, description=description, path=path)
            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.add_share(**kwargs)
                except Exception:
                    logger.exception(f'ERROR in name {name!r} value {value!r}')

    def _sens_availpatches(self, device, name, value_map):
        """Sensor: Applicable Patches."""
        src = {'name': name, 'value_map': value_map}
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            title = self._get_valuedata(name=name, key='Title', value=value)

            state = self._get_valuedata(name=name, key='Install Status', value=value)

            severity = self._get_valuedata(name=name, key='Severity', value=value)

            publish_dt = self._get_valuedata(name=name, key='Release Date', value=value)
            publish_dt = tanium.tools.parse_dt(value=publish_dt, src=src)

            bulletins = self._get_valuedata(name=name, key='Bulletins', value=value)
            bulletins = tanium.tools.parse_csv(value=bulletins, split=' ', src=src)
            bulletins = tanium.tools.listify(value=bulletins, clean=True) or None

            kbs = self._get_valuedata(name=name, key='KB Articles', value=value)
            kbs = tanium.tools.listify(value=kbs, clean=True) or None

            cves = self._get_valuedata(name=name, key='CVE IDs', value=value)
            cves = tanium.tools.parse_csv(value=cves, split=' ', src=src)
            cves = tanium.tools.listify(value=cves, clean=True) or None

            security_bulletin_ids = []

            if isinstance(cves, list):
                security_bulletin_ids += cves

            if isinstance(bulletins, list):
                security_bulletin_ids += bulletins

            security_bulletin_ids = security_bulletin_ids or None

            categories = self._get_valuedata(name=name, key='Classification', value=value)
            categories = tanium.tools.listify(value=categories, clean=True) or None

            kwargs = dict(
                title=title,
                state=state,
                publish_date=publish_dt,
                security_bulletin_ids=security_bulletin_ids,
                kb_article_ids=kbs,
                categories=categories,
            )

            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.add_available_security_patch(**kwargs)
                except Exception:
                    logger.exception(f'ERROR in name {name!r} value {value!r} kwargs {kwargs!r}')

    def _sens_runningprocs(self, device, name, value_map):
        """Sensor: Running Processes."""
        values = value = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            try:
                device.add_process(name=value)
            except Exception:
                logger.exception(f'ERROR in name {name!r} value {value!r}')

    def _sens_listenports(self, device, name, value_map):
        """Sensor: Listen Ports."""
        src = {'name': name, 'value_map': value_map}
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            name = self._get_valuedata(name=name, key='Name', value=value)
            port_id = self._get_valuedata(name=name, key='Local Port', value=value)
            port_id = str(port_id).replace(':', '')
            port_id = tanium.tools.parse_int(value=port_id, src=src)

            open_ports = [x.get_field_safe(attr='port_id') for x in device.open_ports]
            if port_id in open_ports:
                continue

            kwargs = dict(service_name=name, port_id=port_id)

            if not tanium.tools.is_empty_vals(value=kwargs):
                try:
                    device.add_open_port(**kwargs)
                except Exception:
                    logger.exception(f'ERROR in name {name!r} value {value!r} kwargs {kwargs}')

    def _sens_clientver(self, device, name, value_map):
        value = self._get_value(name=name, value_map=value_map, first=True)

        if not tanium.tools.is_empty(value=value):
            device.add_agent_version(agent=AGENT_NAMES.tanium, version=value)

    def _sens_vulnagg(self, device, name, value_map):
        """Sensor: Comply - Vulnerability Aggregates."""
        str_fields = {
            'Engine': 'engine',
            'Hash': 'hash_value',
            'Error Code': 'error_code',
        }

        all_column = 'All'
        all_field = 'count_all'

        count_fields = {
            'Vulnerable': 'count_vulnerable',
            'Nonvulnerable': 'count_non_vulnerable',
            'Error': 'count_error',
            'High Severity': 'count_high_severity',
            'Medium Severity': 'count_medium_severity',
            'Low Severity': 'count_low_severity',
        }

        self.calc_percent_sensor(
            device=device,
            name=name,
            value_map=value_map,
            all_column=all_column,
            all_field=all_field,
            str_fields=str_fields,
            count_fields=count_fields,
            calc_class=VulnerabilityAggregates,
            calc_field='vulnerabilities',
        )

    def _sens_complyagg(self, device, name, value_map):
        """Sensor: Comply - Compliance Aggregates."""
        str_fields = {
            'Engine': 'engine',
            'Hash': 'hash_value',
            'Error Code': 'error_code',
            'Version': 'version',
        }

        all_column = 'All'
        all_field = 'count_all'

        count_fields = {
            'Pass': 'count_pass',
            'Fail': 'count_fail',
            'Error': 'count_error',
            'Unknown': 'count_unknown',
            'Not Applicable': 'count_not_applicable',
            'Not Checked': 'count_not_checked',
            'Not Selected': 'count_not_selected',
            'Informational': 'count_informational',
            'Fixed': 'count_fixed',
        }

        self.calc_percent_sensor(
            device=device,
            name=name,
            value_map=value_map,
            all_column=all_column,
            all_field=all_field,
            str_fields=str_fields,
            count_fields=count_fields,
            calc_class=ComplianceAggregates,
            calc_field='compliance',
        )

    def calc_percent_sensor(
        self, device, name, value_map, all_column, all_field, str_fields, count_fields, calc_class, calc_field
    ):
        values = self._get_value(name=name, value_map=value_map)

        for value in values:
            try:
                calc_obj = calc_class()
                for column, field in str_fields.items():
                    field_value = tanium.tools.parse_str(value=value[column]['value'], src=value[all_column])
                    setattr(calc_obj, field, field_value)

                all_value = tanium.tools.parse_int(value=value[all_column]['value'], src=value[all_column])
                setattr(calc_obj, all_field, all_value)

                for column, field in count_fields.items():
                    field_value = tanium.tools.parse_int(value=value[column]['value'], src=value[column])
                    setattr(calc_obj, field, field_value)

                    if field_value is not None:
                        perc_field = field.replace('count_', 'percent_')
                        perc_value = tanium.tools.calc_percent(part=field_value, whole=all_value)
                        setattr(calc_obj, perc_field, perc_value)

                getattr(device, calc_field).append(calc_obj)
            except Exception:
                logger.exception(f'ERROR in name {name!r} value {value!r}')

    def _get_valuedata(self, name, key, value):
        try:
            if not isinstance(value, dict):
                logger.error(f'IS NOT DICT name {name!r} key {key!r} value {value!r}')
                return None

            if key not in value:
                logger.error(f'name {name!r} missing key {key!r} in value {value!r}')
                return None

            return self._get_value(name=f'{name}:{key}', value_map=value[key])
        except Exception:
            logger.exception(f'ERROR in _getvaluedata name {name!r} key {key!r} value {value!r}')
        return None

    @staticmethod
    def _get_value(name, value_map, first=False):
        src = {'name': name, 'value_map': value_map, 'first': first}
        try:
            if not isinstance(value_map, dict):
                logger.error(f'IS NOT DICT name {name!r} value_map {value_map!r}')
                return None

            if 'value' not in value_map:
                logger.error(f'DOES NOT HAVE "value" KEY name {name!r} value_map {value_map!r}')
                return None

            value = value_map['value']
            value = tanium.tools.parse_skip(value=value, src=src)

            if first:
                return tanium.tools.get_item1(value=value)
            return value
        except Exception:
            logger.exception(f'ERROR in _get_value name {name!r} value_map {value_map!r}')
        return None

    @property
    def _sensor_maps(self):
        return {
            'AD Organizational Unit': self._sens_adorgunit,
            'Applicable Patches': self._sens_availpatches,
            'BIOS Version': self._sens_biosver,
            'Chassis Type': self._sens_chassis,
            'Computer Name': self._sens_hostname,
            'Comply - Compliance Aggregates': self._sens_complyagg,
            'Comply - Vulnerability Aggregates': self._sens_vulnagg,
            'Computer Serial Number': self._sens_serial,
            'CPU Details': self._sens_cpudetails,
            'Custom Tags': self._sens_tags,
            'Domain Member': self._sens_domainmember,
            'Installed Applications': self._sens_instapps,
            'Is Virtual': self._sens_isvirt,
            'Last Logged In User': self._sens_lastuser,
            'Last Reboot': self._sens_lastreboot,
            'Listen Ports': self._sens_listenports,
            'Logged In Users': self._sens_loggedin,
            'Manufacturer': self._sens_manufacturer,
            'Model': self._sens_model,
            'Motherboard Manufacturer': self._sens_mobomanu,
            'Motherboard Version': self._sens_mobover,
            'Open Ports': self._sens_openports,
            'Open Share Details': self._sens_openshares,
            'Operating System Build Number': self._sens_osbuildnum,
            'Operating System Install Date': self._sens_osinstalldt,
            'Operating System': self._sens_opsys,
            'OS Platform': self._sens_osplat,
            'RAM': self._sens_memory,
            'Running Processes': self._sens_runningprocs,
            'Service Details': self._sens_services,
            'Service Pack': self._sens_service_pack,
            'Time Zone': self._sens_timezone,
            'Tanium Client Version': self._sens_clientver,
            'Total Memory': self._sens_memory,
            'Uptime': self._sens_uptime,
        }

    def _get_sensor_maps(self, device_raw):
        try:
            sensor_maps = {x: self._sensor_maps[x] for x in device_raw if x in self._sensor_maps}
        except Exception:
            logger.exception(f'ERROR in _get_sensor_maps device_raw {device_raw} sensor_maps {self._sensor_maps}')
            return {}

        try:
            if not getattr(self, '_has_printed_maps', False):
                self._has_printed_maps = True

                missing = '\n  '.join([x for x in self._sensor_maps if x not in device_raw])
                maps_list = '\n  '.join(list(sensor_maps))
                extra = '\n  '.join([x for x in device_raw if x not in self._sensor_maps])

                logger.info(f'sensors in question and in sensor maps:\n  {maps_list}')
                logger.info(f'sensors in question but not in sensor maps:\n  {extra}')
                logger.info(f'sensors in sensor maps but not in question:\n  {missing}')
        except Exception:
            logger.exception(f'ERROR in _has_printed_maps device_raw {device_raw} sensor_maps {self._sensor_maps}')

        return sensor_maps

    def _create_sq_device(self, device_raw, metadata):
        device_raw, sq_name, question = device_raw

        missing = TaniumSqConnection.missing_sensors(name=sq_name, sensor_names=list(device_raw))
        if missing:
            logger.error(missing)
            return None

        cid_key = 'Computer ID'
        cid = self._get_value(name=cid_key, value_map=device_raw.get(cid_key), first=True)
        cid = tanium.tools.parse_str(value=cid, src=cid_key)

        id_map = {cid_key: cid}
        if tanium.tools.is_empty_vals(value=id_map):
            logger.error(f'Bad device with empty ids {id_map} in {device_raw}')
            return None

        expiration = tanium.tools.parse_dt(value=question.get('expiration'), src=question)

        device = self._new_device_adapter()
        device.last_seen = expiration

        device.os = DeviceAdapterOS()
        device.id = tanium.tools.joiner('SQ_DEVICE', sq_name, cid, join='_')
        device.uuid = cid
        device.sq_name = sq_name
        device.sq_query_text = question.get('query_text')
        device.sq_expiration = expiration
        device.sq_selects = tanium.tools.parse_selects(question=question)
        tanium.tools.set_metadata(device=device, metadata=metadata)
        tanium.tools.set_module_ver(device=device, metadata=metadata, module='interact')

        # handle network sensors, special case logic
        has_network_discover = NET_SENSOR_DISCOVER in device_raw
        has_network_base = all([x in device_raw for x in NET_SENSORS])

        # they have the network sensor from discover, which we prefer to use
        # since it has IP and MAC index correlated
        try:
            if has_network_discover:
                self._sens_netadapters(
                    device=device, name=NET_SENSOR_DISCOVER, value_map=device_raw[NET_SENSOR_DISCOVER],
                )
            # they only have the network sensors from the base content, which is horrible
            # since we do not know which IP maps to which MAC
            elif has_network_base:
                self._sens_ipmac(device=device, device_raw=device_raw)
            # they don't have either, we won't process it
            else:
                logger.error(f'device_raw did not contain {NET_SENSOR_DISCOVER} or {NET_SENSORS}')
                return None
        except Exception:
            logger.exception('Failure while parsing network information')
            return None

        # parse out the things we know to parse into aggregated data
        sensor_maps = self._get_sensor_maps(device_raw=device_raw)
        for name, handler in sensor_maps.items():
            try:
                handler(device=device, name=name, value_map=device_raw[name])
            except Exception:
                logger.exception(f'Failure in name {name!r} handler {handler!r}')

        # parse out everything, creating dynamic fields as necessary
        for name, value_map in device_raw.items():
            try:
                handler = self.handle_complex if value_map['type'] == 'object' else self.handle_simple
                handler(device=device, name=name, value_map=value_map)
            except Exception:
                msg = f'Failure in dynamic field handling with sensor name {name!r} value_map {value_map!r}'
                logger.exception(msg)

        device.set_raw(device_raw)
        return device

    def handle_simple(self, device, name, value_map):
        """Handle a simple sensor.

        device: device adapter for this asset
        name: name of sensor: 'BIOS Version'
        value_type: the value type defined in the sensor from tanium
        value: dict for this single column sensor: {'type': 'Version', 'value': ['4.2.amazon']}
        """
        field_title = f'Sensor: {name}'
        field_name = normalize_var_name(f'sensor_{name}').lower().strip()
        field = device.get_field_type(field_name=field_name)

        value_map = self.parse_value_map(name=name, value_map=value_map, field=field)
        values = value_map.get('value', []) or []

        if not field:
            field = ListField(
                field_type=value_map.get('field_type', str),
                json_format=value_map.get('field_fmt', None),
                title=field_title,
            )

            logger.debug(f'NEW SIMPLE FIELD name: {field_name!r}, title: {field_title!r}')
            device.declare_new_field(field_name=field_name, field_value=field)

        if isinstance(values, list):
            for value in values:
                try:
                    device[field_name].append(value)
                except Exception:
                    logger.exception(f'ERROR appending value {value!r} from values {values!r} to field {field_name!r}')

    def handle_complex(self, device, name, value_map):
        """Handle a complex sensor.

        device: device adapter for this asset
        name: name of sensor: 'Listen Ports'
        value_map: {
            'type': 'object',
            'value': [{'Local Port': {'type': 'String', 'value': ':22'}, 'Name': {'type': 'String', 'value': 'sshd'}}],
        }
        """
        items = value_map['value']

        field_title = f'Sensor: {name}'
        field_name = normalize_var_name(f'sensor_{name}').lower().strip()
        field = device.get_field_type(field_name=field_name)

        if not field:
            field = ListField(field_type=new_complex(), title=field_title)

            logger.debug(f'NEW COMPLEX FIELD name: {field_name!r}, title: {field_title!r}')
            device.declare_new_field(field_name=field_name, field_value=field)

        for item in items:
            has_value, item_instance = self.handle_complex_sub_field(item=item, parent=field, parent_name=name)

            if not has_value:
                continue

            try:
                device[field_name].append(item_instance)
            except Exception:
                logger.exception(f'ERROR appending instance of item {item!r} to field {field_name!r}')

    def handle_complex_sub_field(self, item, parent, parent_name):
        has_value = False
        item_instance = parent.type()

        for name, value_map in item.items():
            try:
                field_title = name
                field_name = normalize_var_name(name).lower().strip()
                field = item_instance.get_field_type(field_name=field_name)

                value_map = self.parse_value_map(name=name, value_map=value_map, field=field, parent_name=parent_name)
                use_list = value_map.get('use_list', False)

                if not field:
                    use_field = ListField if use_list else Field
                    field = use_field(
                        field_type=value_map.get('field_type', str),
                        json_format=value_map.get('field_fmt', None),
                        title=field_title,
                    )
                    msg = (
                        f'new sub field name: {field_name!r}, title: {field_title!r}, parent: {parent.title!r}'
                        f', use_list {use_list}'
                    )
                    logger.debug(msg)
                    item_instance.declare_new_field(field_name=field_name, field_value=field)

                src_value = value_map.get('value', None)
                if use_list:
                    values = tanium.tools.listify(value=src_value, clean=True)
                    for value in values:
                        item_instance[field_name].append(value)
                        has_value = True
                else:
                    if not tanium.tools.is_empty(value=src_value):
                        item_instance[field_name] = src_value
                        has_value = True
            except Exception:
                logger.exception(f'ERROR with name {name!r} value_map {value_map!r}')

        return has_value, item_instance

    @staticmethod
    def parse_network_adapters(src):
        value_map = src['value_map']
        value = value_map['value']
        value = tanium.tools.parse_csv(value=value, src=src)
        value = tanium.tools.parse_ip(value=value, src=src)
        return {
            'value': value,
            'type': value_map['type'],
            'field_type': str,
            'field_fmt': JsonStringFormat.ip,
            'use_list': True,
        }

    @property
    def over_complex(self):
        return {'Network Adapters': {'IP Address': self.parse_network_adapters}}

    @property
    def over_simple(self):
        return {}

    # pylint: disable=too-many-branches, too-many-statements
    def parse_value_map(self, name, value_map, field, parent_name=None):
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
        src = {'name': name, 'parent_name': parent_name, 'field': field, 'value_map': value_map}
        value = value_map['value']
        value = tanium.tools.parse_skip(value=value, src=src)
        value_type = value_map['type']
        field_fmt = None
        field_type = str
        use_list = False

        try:
            if parent_name and parent_name in self.over_complex and name in self.over_complex[parent_name]:
                overmethod = self.over_complex[parent_name][name]
                # logger.debug(f'Implementing override for {parent_name!r}:{name!r}:{overmethod}')
                return overmethod(src=src)
            if name in self.over_simple:
                overmethod = self.over_simple[name]
                # logger.debug(f'Implementing override for {parent_name!r}:{name!r}:{overmethod}')
                return overmethod(src=src)
            if value_type == 'NumericInteger':
                if tanium.tools.is_float(value=value):
                    field_type = float
                    value = tanium.tools.parse_float(value=value, src=src)
                else:
                    field_type = int
                    value = tanium.tools.parse_int(value=value, src=src)
                field_fmt = None
            elif value_type == 'Version':
                field_fmt = JsonStringFormat.version
                field_type = str
            elif value_type in ['BESDate', 'WMIDate']:
                field_fmt = JsonStringFormat.date_time
                field_type = datetime.datetime
                value = tanium.tools.parse_dt(value=value, src=src)
            elif value_type == 'IPAddress':
                field_fmt = JsonStringFormat.ip
                field_type = str
                value = tanium.tools.parse_ip(value=value, src=src)

            # deal with conflicting value types for pre-existing fields
            if field and field_type == str and field_fmt is None:
                if field.type == datetime.datetime:
                    field_type = datetime.datetime
                    value = tanium.tools.parse_dt(value=value, src=src)
                elif field.format == JsonStringFormat.ip:
                    field_fmt = JsonStringFormat.ip
                    value = tanium.tools.parse_ip(value=value, src=src)
                elif field.type == int:
                    field_type = int
                    value = tanium.tools.parse_int(value=value, src=src)
                elif field.type == float:
                    field_type = float
                    value = tanium.tools.parse_float(value=value, src=src)
        except Exception:
            msg = f'ERROR in parse_value_map in {parent_name!r}:{name!r} with value_map {value_map!r} and field {field}'
            logger.exception(msg)
        return {
            'value': value,
            'type': value_type,
            'field_type': field_type,
            'field_fmt': field_fmt,
            'use_list': use_list,
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, metadata in devices_raw_data:
            device = None
            try:
                device = self._create_sq_device(device_raw=device_raw, metadata=metadata)
            except Exception:
                msg = f'ERROR in creating Saved Question Device {device_raw}'
                logger.exception(msg)

            if device:
                yield device

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {'name': 'domain', 'title': 'Hostname or IP Address', 'type': 'string'},
                {'name': 'username', 'title': 'User Name', 'type': 'string'},
                {'name': 'password', 'title': 'Password', 'type': 'string', 'format': 'password'},
                {'name': 'sq_name', 'type': 'string', 'title': 'Names of Saved Questions to fetch (comma separated)'},
                {'name': 'sq_refresh', 'title': 'Re-ask every fetch', 'type': 'bool', 'default': REFRESH},
                {
                    'name': 'sq_max_hours',
                    'title': 'Re-ask if results are older than N hours',
                    'type': 'integer',
                    'default': MAX_HOURS,
                },
                {
                    'name': 'no_results_wait',
                    'title': 'Re-asking waits until all answers are returned',
                    'type': 'bool',
                    'default': NO_RESULTS_WAIT,
                },
                {'name': 'verify_ssl', 'title': 'Verify SSL', 'type': 'bool'},
                {'name': 'https_proxy', 'title': 'HTTPS Proxy', 'type': 'string'},
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl',
                'sq_name',
                'sq_refresh',
                'no_results_wait',
                'sq_max_hours',
            ],
            'type': 'array',
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {'name': 'page_size', 'title': 'Number of assets to fetch per page', 'type': 'integer'},
                {
                    'name': 'page_sleep',
                    'title': 'Number of seconds to wait in between each page fetch',
                    'type': 'integer',
                },
            ],
            'required': ['page_size', 'page_sleep'],
            'pretty_name': 'Tanium Interact Configuration',
            'type': 'array',
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'page_size': PAGE_SIZE,
            'page_sleep': SLEEP_GET_ANSWERS,
        }

    def _on_config_update(self, config):
        logger.info(f'Loading Tanium Interact config: {config}')
        self._page_size = config.get('page_size', PAGE_SIZE)
        self._page_sleep = config.get('page_sleep', SLEEP_GET_ANSWERS)
