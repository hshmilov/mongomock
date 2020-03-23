import datetime
import logging
import re

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter, DeviceAdapterOS, DeviceAdapterCPU, AGENT_NAMES
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.utils.files import get_local_config_file
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import normalize_var_name
from axonius.clients import tanium
from tanium_sq_adapter.consts import STRONG_SENSORS
from tanium_sq_adapter.connection import TaniumSqConnection

logger = logging.getLogger(f'axonius.{__name__}')


def new_complex():

    class ComplexSensor(SmartJsonClass):
        pass

    return ComplexSensor


class TaniumSqAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        server_name = Field(field_type=str, title='Tanium Server')
        server_version = Field(field_type=str, title='Tanium Server Version', json_format=JsonStringFormat.version)
        module_version = Field(field_type=str, title='Module Version', json_format=JsonStringFormat.version)
        sq_name = Field(field_type=str, title='Saved Question Name')
        sq_query_text = Field(field_type=str, title='Question Query Text')
        sq_expiration = Field(field_type=datetime.datetime, title='Question Last Asked')
        sq_selects = ListField(field_type=str, title='Question Selects')

    def __init__(self, *args, **kwargs):
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
        connection = TaniumSqConnection(
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

    def _sens_hostname(self, device, name, value_map):
        """Sensor: Computer Name."""
        value = self._get_value(name=name, value_map=value_map, first=True)

        if not tanium.tools.is_empty(value=value):
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

    def _sens_cpudetails(self, device, name, value_map):
        """Sensor: CPU Details."""
        src = {'name': name, 'value_map': value_map}
        values = self._get_value(name=name, value_map=value_map, first=False)
        values = tanium.tools.listify(value=values, clean=True)

        for value in values:
            arch = self._get_valuedata(name=name, key='System Type', value=value)

            if '64' in str(arch):
                bitness = 64
                arch = 'x64'
            elif 'x86' in str(arch):
                bitness = 32
                arch = 'x86'
            else:
                valids = DeviceAdapterCPU().enum
                matches = [x for x in [re.search(v, arch) for v in valids] if x]
                arch = matches[0] if matches else None
                bitness = None

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
            'Network Adapters': self._sens_netadapters,
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

        cid_key = 'Computer ID'
        cid = self._get_value(name=cid_key, value_map=device_raw.get(cid_key), first=True)
        cid = tanium.tools.parse_str(value=cid, src=cid_key)

        id_map = {cid_key: cid}
        if tanium.tools.is_empty_vals(value=id_map):
            logger.error(f'Bad device with empty ids {id_map} in {device_raw}')
            return None

        if not any([x in STRONG_SENSORS for x in device_raw]):
            found_sensors = ', '.join(list(device_raw))
            strong_sensors = ', '.join(STRONG_SENSORS)
            msg = [
                f'Saved Question: No strong identifier sensor found in {sq_name!r}',
                f'Strong identifier sensors: {strong_sensors}',
                f'Found sensors: {found_sensors}',
            ]
            logger.error('\n -- '.join(msg))
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
                {'name': 'sq_refresh', 'title': 'Re-ask every fetch', 'type': 'bool', 'default': False},
                {
                    'name': 'sq_max_hours',
                    'title': 'Re-ask if results are older than N hours',
                    'type': 'integer',
                    'default': 6,
                },
                {
                    'name': 'no_results_wait',
                    'title': 'Re-asking waits until all answers are returned',
                    'type': 'bool',
                    'default': True,
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
