import datetime
import logging
import re

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter, DeviceAdapterOS, DeviceAdapterCPU, AGENT_NAMES
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.utils.files import get_local_config_file

from axonius.clients import tanium

from tanium_sq_adapter.connection import TaniumSqConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TaniumSqAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        server_name = Field(field_type=str, title='Server')
        server_version = Field(field_type=str, title='Server Version', json_format=JsonStringFormat.version)
        sq_name = Field(field_type=str, title='Saved Question Name')
        query_text = Field(field_type=str, title='Question Query Text')
        expiration = Field(field_type=datetime.datetime, title='Question Last Asked')
        selects = ListField(field_type=str, title='Question Selects')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain'] + '_' + client_config['username'] + '_' + client_config['sq_name']

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
            msg = f'Error connecting to client at {domain!r}, reason: {exc}'
            logger.exception(msg)
            raise ClientConnectionException(msg)

    def _query_devices_by_client(self, client_name, client_data):
        connection, client_config = client_data
        with connection:
            yield from connection.get_device_list(client_name=client_name, client_config=client_config)

    def _sens_hostname(self, device, sname, sdata):
        """Sensor: Computer Name."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            device.hostname = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_serial(self, device, sname, sdata):
        """Sensor: Computer Serial Number."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            device.device_serial = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_instapps(self, device, sname, sdata):
        """Sensor: Installed Applications."""
        values = tanium.tools.listify(value=self._get_value(sname=sname, sdata=sdata, first=False), clean=True)

        for value in values:
            name = self._get_valuedata(sname=sname, key='Name', value=value, first=True)
            version = self._get_valuedata(sname=sname, key='Version', value=value, first=True)

            try:
                device.add_installed_software(name=name, version=version)
            except Exception:
                logger.exception(f'Problem with sname {sname!r} value {value!r}')

    def _sens_chassis(self, device, sname, sdata):
        """Sensor: Chassis Type."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        if 'virtual' in str(value).lower() and tanium.tools.check_attr(device, 'virtual_host') is None:
            device.virtual_host = True

    def _sens_lastuser(self, device, sname, sdata):
        """Sensor: Last Logged In User."""
        values = tanium.tools.listify(self._get_value(sname=sname, sdata=sdata, first=False))

        try:
            for value in values:
                if value not in device.last_used_users:
                    device.last_used_users.append(value)
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_lastreboot(self, device, sname, sdata):
        """Sensor: Last Reboot."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)
        value = tanium.tools.parse_dt(value)

        try:
            if tanium.tools.check_attr(device, 'boot_time') is None:
                device.boot_time = value

            if tanium.tools.check_attr(device, 'uptime') is None:
                try:
                    device.uptime = (tanium.tools.dt_now(utc=True) - value).days
                except Exception:
                    device.uptime = (tanium.tools.dt_now(utc=False) - value).days
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_model(self, device, sname, sdata):
        """Sensor: Model."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            device.device_model = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_manufacturer(self, device, sname, sdata):
        """Sensor: Manufacturer."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            device.device_manufacturer = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_tags(self, device, sname, sdata):
        """Sensor: Custom Tags."""
        values = tanium.tools.listify(self._get_value(sname=sname, sdata=sdata, first=False), clean=True)

        try:
            for value in values:
                device.add_key_value_tag(key=value, value=None)
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_openports(self, device, sname, sdata):
        """Sensor: Open Ports."""
        values = tanium.tools.listify(self._get_value(sname=sname, sdata=sdata, first=False), clean=True)

        for value in values:
            value = tanium.tools.parse_int(value)

            try:
                for open_port in device.open_ports:
                    if tanium.tools.check_attr(open_port, 'port_id') == value:
                        continue

                device.add_open_port(port_id=value)
            except Exception:
                logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_cpudetails(self, device, sname, sdata):
        """Sensor: CPU Details."""
        values = self._get_value(sname=sname, sdata=sdata, first=False)

        for value in values:
            arch = self._get_valuedata(sname=sname, key='System Type', value=value, first=True)

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

            cpu = self._get_valuedata(sname=sname, key='CPU', value=value, first=True)

            ghz = self._get_valuedata(sname=sname, key='CPU Speed', value=value, first=True)
            ghz = str(ghz).lower().replace('mhz', '').strip()
            ghz = tanium.tools.parse_int(ghz) / 1000

            cores = self._get_valuedata(sname=sname, key='Total Cores', value=value, first=True)
            cores = tanium.tools.parse_int(cores)

            try:
                device.add_cpu(name=cpu, bitness=bitness, cores=cores, architecture=arch, ghz=ghz)
            except Exception:
                logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_netadapters(self, device, sname, sdata):
        """Sensor: Network Adapters."""
        values = tanium.tools.listify(value=self._get_value(sname=sname, sdata=sdata, first=False), clean=True)

        for value in values:
            ips = self._get_valuedata(sname=sname, key='IP Address', value=value, first=True)
            ips = tanium.tools.listify(value=tanium.tools.parse_ip(ips), clean=True)

            mac = self._get_valuedata(sname=sname, key='MAC Address', value=value, first=True)
            mac = tanium.tools.parse_mac(mac)

            try:
                device.add_nic(ips=ips, mac=mac)
            except Exception:
                logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_opsys(self, device, sname, sdata):
        """Sensor: Operating System."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            device.figure_os(value)
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_services(self, device, sname, sdata):
        """Sensor: Service Details."""
        values = tanium.tools.listify(value=self._get_value(sname=sname, sdata=sdata, first=False), clean=True)

        for value in values:
            dname = self._get_valuedata(sname=sname, key='Service Display Name', value=value, first=True)
            status = self._get_valuedata(sname=sname, key='Service Status', value=value, first=True)
            name = self._get_valuedata(sname=sname, key='Service Name', value=value, first=True)

            try:
                device.add_service(name=name, display_name=dname, status=status)
            except Exception:
                logger.exception(f'Problem with sname {sname!r} value {value!r}')

    def _sens_service_pack(self, device, sname, sdata):
        """Sensor: Service Pack."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            if tanium.tools.check_attr(device.os, 'sp') is None:
                device.os.sp = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_memory(self, device, sname, sdata):
        """Sensors: RAM, Total Memory."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            value = str(value).lower().replace('mb', '').strip()
            value = tanium.tools.parse_int(value)
            if value:
                value = value / 1024
                device.total_physical_memory = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_uptime(self, device, sname, sdata):
        """Sensor: Uptime."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)
        value = tanium.tools.parse_int(str(value).lower().replace('days', '').strip())

        try:

            if tanium.tools.check_attr(device, 'uptime') is None:
                device.uptime = value

            if tanium.tools.check_attr(device, 'boot_time') is None:
                try:
                    device.boot_time = tanium.tools.dt_now(utc=True) - datetime.timedelta(days=value)
                except Exception:
                    device.boot_time = tanium.tools.dt_now(utc=False) - datetime.timedelta(days=value)

        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_osplat(self, device, sname, sdata):
        """Sensor: OS Platform."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        if not device.os.type:
            try:
                device.os.type = value
            except Exception:
                logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_osinstalldt(self, device, sname, sdata):
        """Sensor: Operating System Install Date."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)
        value = tanium.tools.parse_dt(value)

        if tanium.tools.check_attr(device.os, 'install_date') is None:
            try:
                device.os.install_date = value
            except Exception:
                logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_osbuildnum(self, device, sname, sdata):
        """Sensor: Operating System Build Number."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        if tanium.tools.check_attr(device.os, 'build') is None:
            try:
                device.os.build = value
            except Exception:
                logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_loggedin(self, device, sname, sdata):
        """Sensor: Logged In Users."""
        values = tanium.tools.listify(self._get_value(sname=sname, sdata=sdata, first=False))

        try:
            for value in values:
                if value not in device.last_used_users:
                    device.last_used_users.append(value)
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} values {values!r}')

        try:
            if values and tanium.tools.check_attr(device, 'current_logged_user') is None:
                device.current_logged_user = values[0]
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} values {values!r}')

    def _sens_domainmember(self, device, sname, sdata):
        """Sensor: Domain Member."""
        value = tanium.tools.parse_bool(self._get_value(sname=sname, sdata=sdata, first=True))

        try:
            device.part_of_domain = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_timezone(self, device, sname, sdata):
        """Sensor: Time Zone."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            device.time_zone = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_biosver(self, device, sname, sdata):
        """Sensor: BIOS Version."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            device.bios_version = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_isvirt(self, device, sname, sdata):
        """Sensor: Is Virtual."""
        value = tanium.tools.parse_bool(self._get_value(sname=sname, sdata=sdata, first=True))

        if tanium.tools.check_attr(device.os, 'virtual_host') is None:
            try:
                device.virtual_host = value
            except Exception:
                logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_mobomanu(self, device, sname, sdata):
        """Sensor: Motherboard Manufacturer."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            device.motherboard_manufacturer = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_mobover(self, device, sname, sdata):
        """Sensor: Motherboard Version."""
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            device.motherboard_version = value
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _sens_adorgunit(self, device, sname, sdata):
        """Sensor: AD Organizational Unit."""
        values = tanium.tools.listify(self._get_value(sname=sname, sdata=sdata, first=False))

        try:
            for value in values:
                if value not in device.organizational_unit:
                    device.organizational_unit.append(value)
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {values!r}')

    def _sens_openshares(self, device, sname, sdata):
        """Sensor: Open Share Details."""
        values = tanium.tools.listify(value=self._get_value(sname=sname, sdata=sdata, first=False), clean=True)
        for value in values:
            name = self._get_valuedata(sname=sname, key='Name', value=value, first=True)
            description = self._get_valuedata(sname=sname, key='Type', value=value, first=True)
            path = self._get_valuedata(sname=sname, key='Path', value=value, first=True)

            try:
                device.add_share(name=name, description=description, path=path)
            except Exception:
                logger.exception(f'Problem with sname {sname!r} value {value!r}')

    def _sens_availpatches(self, device, sname, sdata):
        """Sensor: Applicable Patches."""
        values = tanium.tools.listify(value=self._get_value(sname=sname, sdata=sdata, first=False), clean=True)

        for value in values:
            title = self._get_valuedata(sname=sname, key='Title', value=value, first=True)
            state = self._get_valuedata(sname=sname, key='Install Status', value=value, first=True)
            severity = self._get_valuedata(sname=sname, key='Severity', value=value, first=True)

            publish_dt = self._get_valuedata(sname=sname, key='Release Date', value=value, first=True)
            publish_dt = tanium.tools.parse_dt(publish_dt)

            bulletins = tanium.tools.listify(
                self._get_valuedata(sname=sname, key='Bulletins', value=value, first=False)
            )
            kbs = tanium.tools.listify(self._get_valuedata(sname=sname, key='KB Articles', value=value, first=False))

            categories = tanium.tools.listify(
                self._get_valuedata(sname=sname, key='Classification', value=value, first=False)
            )

            try:
                device.add_available_security_patch(
                    title=title,
                    state=state,
                    publish_date=publish_dt,
                    security_bulletin_ids=bulletins,
                    kb_article_ids=kbs,
                    categories=categories,
                )
            except Exception:
                logger.exception(f'Problem with sname {sname!r} value {value!r}')

    def _sens_runningprocs(self, device, sname, sdata):
        """Sensor: Running Processes."""
        values = tanium.tools.listify(value=self._get_value(sname=sname, sdata=sdata, first=False), clean=True)

        for value in values:
            try:
                device.add_process(name=value)
            except Exception:
                logger.exception(f'Problem with sname {sname!r} value {value!r}')

    def _sens_listenports(self, device, sname, sdata):
        """Sensor: Listen Ports."""
        values = tanium.tools.listify(value=self._get_value(sname=sname, sdata=sdata, first=False), clean=True)

        for value in values:
            name = self._get_valuedata(sname=sname, key='Name', value=value, first=True)
            port_id = self._get_valuedata(sname=sname, key='Local Port', value=value, first=True)
            port_id = tanium.tools.parse_int(str(port_id).replace(':', ''))

            try:
                for open_port in device.open_ports:
                    if open_port.port_id == port_id:
                        continue
                device.add_open_port(service_name=name, port_id=port_id)
            except Exception:
                logger.exception(f'Problem with sname {sname!r} value {value!r}')

    def _sens_clientver(self, device, sname, sdata):
        value = self._get_value(sname=sname, sdata=sdata, first=True)

        try:
            device.add_agent_version(agent=AGENT_NAMES.tanium, version=value)
        except Exception:
            logger.exception(f'Problem with sname {sname!r} sdata {sdata!r} value {value!r}')

    def _get_valuedata(self, sname, key, value, first=True):
        try:
            if key in value:
                return self._get_value(sname=f'{sname!r}:{key}', sdata=value[key], first=first)
            logger.error(f'sname {sname!r} missing key {key} in value {value!r}')
            return None
        except Exception:
            logger.exception(f'Problem in _getvaluedata sname {sname!r} key {key!r} value {value!r} first {first!r}')
        return None

    @staticmethod
    def _get_value(sname, sdata, first=False):
        try:
            if not isinstance(sdata, dict):
                logger.error(f'IS NOT DICT sname {sname!r} sdata {sdata!r}')
                return None

            if 'value' not in sdata:
                logger.error(f'DOES NOT HAVE "value" KEY sname {sname!r} sdata {sdata!r}')
                return None

            value = sdata['value']
            value = tanium.tools.parse_skip(value)

            if first:
                return tanium.tools.get_item1(value)
            return value
        except Exception:
            logger.exception(f'Problem in _get_value sname {sname!r} sdata {sdata!r}')
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
            sensor_maps = {}
            missing = []
            extra = []

            for sensor in device_raw:
                if sensor in self._sensor_maps:
                    sensor_maps[sensor] = self._sensor_maps[sensor]
                else:
                    extra.append(sensor)

            for sensor_map in self._sensor_maps:
                if sensor_map not in device_raw:
                    missing.append(sensor_map)

            if not getattr(self, '_printed_maps', False):
                self._printed_maps = True
                lsensor_maps = '\n  '.join(list(sensor_maps))
                lextra = '\n  '.join(extra)
                lmissing = '\n  '.join(missing)
                logger.info(f'sensors in question and in sensor maps:\n  {lsensor_maps}')
                logger.info(f'sensors in question but not in sensor maps:\n  {lextra}')
                logger.info(f'sensors in sensor maps but not in question:\n  {lmissing}')
            return sensor_maps
        except Exception:
            logger.exception(f'Problem in _get_sensor_maps device_raw {device_raw} sensor_maps {self._sensor_maps}')
        return {}

    def _create_sq_device(self, device_raw, metadata):
        device_raw, sq_name, question = device_raw

        dvc_id_attr = 'Computer ID'

        if dvc_id_attr not in device_raw:
            msg = f'NO {dvc_id_attr!r} ATTR DEFINED IN {device_raw!r}'
            logger.error(msg)
            return None

        dvc_id = self._get_value(sname=dvc_id_attr, sdata=device_raw.get(dvc_id_attr), first=True)

        if not dvc_id:
            msg = f'EMPTY VALUE IN {dvc_id_attr!r} ATTR IN {device_raw!r}'
            logger.error(msg)
            return None

        dvc_id = str(dvc_id)

        expiration = tanium.tools.parse_dt(question.get('expiration'))

        device = self._new_device_adapter()
        device.last_seen = expiration

        device.os = DeviceAdapterOS()
        device.id = '_'.join(['SQ_DEVICE', sq_name, dvc_id])
        device.uuid = dvc_id
        device.sq_name = sq_name
        device.query_text = question.get('query_text')
        device.expiration = expiration
        device.selects = tanium.tools.parse_selects(question)
        tanium.tools.set_metadata(device=device, metadata=metadata)

        sensor_maps = self._get_sensor_maps(device_raw=device_raw)

        # parse out the things we know to parse
        for sname, smethod in sensor_maps.items():
            sdata = device_raw[sname]
            try:
                smethod(device=device, sname=sname, sdata=sdata)
            except Exception:
                logger.exception(f'Failure in sname {sname!r} smethod {smethod!r} sdata {sdata!r}')

        # parse out everything, creating dynamic fields as necessary
        for sname, sdata in device_raw.items():
            try:
                tanium.tools.put_tanium_sq_dynamic_field(entity=device, name=sname, value_map=sdata, is_sub_field=False)
            except Exception:
                msg = f'Failure in put_tanium_sq_dynamic_field sname {sname!r} with sdata {sdata!r}'
                logger.exception(msg)

        device.set_raw(device_raw)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, metadata in devices_raw_data:
            device = None
            try:
                device = self._create_sq_device(device_raw=device_raw, metadata=metadata)
            except Exception:
                msg = f'Problem with creating Saved Question Device {device_raw}'
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
