import logging
from datetime import timedelta

logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, adapter_consts, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.ad_entity import ADEntity
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_organizational_units_from_dn
from sccm_adapter.connection import SccmConnection
import sccm_adapter.consts as consts
from sccm_adapter.exceptions import SccmException


class SccmAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter, ADEntity):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self.devices_fetched_at_a_time = int(self.config['DEFAULT'][consts.DEVICES_FETECHED_AT_A_TIME])

    def _get_client_id(self, client_config):
        return client_config[consts.SCCM_HOST]

    def _connect_client(self, client_config):
        try:
            connection = SccmConnection(database=client_config[consts.SCCM_DATABASE],
                                        server=client_config[consts.SCCM_HOST],
                                        port=client_config.get(consts.SCCM_PORT) or consts.DEFAULT_SCCM_PORT,
                                        devices_paging=self.devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception:
            message = f"Error connecting to client with parameters {str(client_config)} "
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            if self._last_seen_timedelta < timedelta(0):
                return list(client_data.query(consts.SCCM_QUERY.format('')))
            else:
                return list(client_data.query(consts.SCCM_QUERY.format(
                    consts.LIMIT_SCCM_QUERY.format(self._last_seen_timedelta.total_seconds() / 3600))))

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": consts.SCCM_HOST,
                    "title": "SCCM/MSSQL Server",
                    "type": "string"
                },
                {
                    "name": consts.SCCM_PORT,
                    "title": "Port",
                    "type": "integer",
                    "default": consts.DEFAULT_SCCM_PORT
                },
                {
                    "name": consts.SCCM_DATABASE,
                    "title": "Database",
                    "type": "string"
                },
                {
                    "name": consts.USER,
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": consts.PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                consts.SCCM_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.SCCM_DATABASE
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device_id = device_raw.get('Distinguished_Name0')
            if not device_id:
                logger.error(f'Got a device with no distinguished name {device_raw}')
                continue
            device = self._new_device_adapter()
            device.id = device_id
            device.organizational_unit = get_organizational_units_from_dn(device_id)
            domain = device_raw.get('Full_Domain_Name0')
            device.hostname = device_raw.get('Netbios_Name0')
            if domain and device.hostname:
                device.hostname += '.' + domain
                device.part_of_domain = True
                device.domain = domain
            device.figure_os((device_raw.get('Caption0') or '') + (device_raw.get("Operating_System_Name_and0") or ''))
            for nic in (device_raw.get('Network Interfaces') or '').split(';'):
                try:
                    if nic == '':
                        continue  # We dont need empty nics of course
                    mac, ips = nic.split('@')
                    device.add_nic(mac, ips.split(', '))
                except Exception:
                    logger.warning(f"Caught weird NIC {nic} for device id {device.id}")
                    pass
            free_physical_memory = device_raw.get('FreePhysicalMemory0')
            device.free_physical_memory = float(free_physical_memory) if free_physical_memory else None
            total_physical_memory = device_raw.get('TotalPhysicalMemory0')
            device.total_physical_memory = float(device_raw.get('TotalPhysicalMemory0')) \
                if total_physical_memory else None
            if total_physical_memory and free_physical_memory:
                device.physical_memory_percentage = 100 * \
                    (1 - device.free_physical_memory / device.total_physical_memory)

            device.device_model = device_raw.get('Model0')
            device.device_manufacturer = device_raw.get('Manufacturer0')
            processes = device_raw.get('NumberOfProcesses0')
            device.number_of_processes = int(processes) if processes else None
            processors = device_raw.get('NumberOfProcessors0')
            device.total_number_of_physical_processors = int(processors) if processors else None

            device.current_logged_user = device_raw.get('UserName0') or device_raw.get('User_Name0')
            device.time_zone = device_raw.get('CurrentTimeZone0')
            device.boot_time = device_raw.get('LastBootUpTime0')
            device.last_seen = device_raw.get('Last Seen')
            device.set_raw(device_raw)
            yield device

    def _correlation_cmds(self):
        logger.error("correlation_cmds is not implemented for sccm adapter")
        raise NotImplementedError("correlation_cmds is not implemented for sccm adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        logger.error("_parse_correlation_results is not implemented for sccm adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for sccm adapter")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
