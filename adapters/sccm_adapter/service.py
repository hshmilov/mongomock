import datetime
import logging

logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.datetime import parse_date
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.ad_entity import ADEntity
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_organizational_units_from_dn, get_exception_string
from axonius.clients.mssql.connection import MSSQLConnection
import sccm_adapter.consts as consts
from axonius.fields import Field, ListField


class SccmAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter, ADEntity):
        resource_id = Field(str, 'Resource ID')
        top_user = Field(str, 'Top Console User')
        macs_no_ip = ListField(str, 'MAC addresses with No IP')
        sccm_type = Field(str, 'SCCM Computer Type')
        sccm_product_type = Field(str, 'SCCM Product Type')
        malware_engine_version = Field(str, 'Malware Protection Engine Version')
        malware_version = Field(str, 'Malware Protection Version')
        malware_product_status = Field(str, 'Malware Protection Product Status')
        malware_last_full_scan = Field(datetime.datetime, 'Malware Protecion Last Full Scan')
        malware_last_quick_scan = Field(datetime.datetime, 'Malware Protecion Last Quick Scan')
        malware_enabled = Field(str, 'Malware Protecion Enabled Status')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self.devices_fetched_at_a_time = int(self.config['DEFAULT'][consts.DEVICES_FETECHED_AT_A_TIME])

    def _get_client_id(self, client_config):
        return client_config[consts.SCCM_HOST]

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config[consts.SCCM_DATABASE],
                                         server=client_config[consts.SCCM_HOST],
                                         port=client_config.get(consts.SCCM_PORT) or consts.DEFAULT_SCCM_PORT,
                                         devices_paging=self.devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f"Error connecting to client host: {str(client_config[consts.SCCM_HOST])}  " \
                      f"database: {str(client_config[consts.SCCM_DATABASE])}"
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        try:
            client_data.connect()

            asset_top_dict = dict()
            try:
                for asset_top_data in client_data.query(consts.USERS_TOP_QUERY):
                    asset_id = asset_top_data.get('ResourceID')
                    if not asset_id:
                        continue
                    asset_top_dict[asset_id] = asset_top_data
            except Exception:
                logger.exception(f'Problem getting top users')

            asset_malware_dict = dict()
            try:
                for asset_malware_data in client_data.query(consts.MALWARE_QUERY):
                    asset_id = asset_malware_data.get('ResourceID')
                    if not asset_id:
                        continue
                    asset_malware_dict[asset_id] = asset_malware_data
            except Exception:
                logger.exception(f'Problem getting malware data')

            asset_users_dict = dict()
            try:
                for asset_users_data in client_data.query(consts.USERS_QUERY):
                    asset_id = asset_users_data.get('MachineResourceID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_users_dict:
                        asset_users_dict[asset_id] = []
                    asset_users_dict[asset_id].append(asset_users_data)
            except Exception:
                logger.exception(f'Problem getting query users')

            asset_software_dict = dict()
            try:
                for asset_soft_data in client_data.query(consts.QUERY_SOFTWARE):
                    asset_id = asset_soft_data.get('ResourceID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_software_dict:
                        asset_software_dict[asset_id] = []
                    asset_software_dict[asset_id].append(asset_soft_data)
            except Exception:
                logger.exception(f'Problem getting query software')

            asset_program_dict = dict()
            try:
                for asset_program_data in client_data.query(consts.QUERY_PROGRAM):
                    asset_id = asset_program_data.get('ResourceID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_program_dict:
                        asset_program_dict[asset_id] = []
                    asset_program_dict[asset_id].append(asset_program_data)
            except Exception:
                logger.exception(f'Problem getting query program')

            try:
                for asset_program_data in client_data.query(consts.QUERY_PROGRAM_2):
                    asset_id = asset_program_data.get('ResourceID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_program_dict:
                        asset_program_dict[asset_id] = []
                    asset_program_dict[asset_id].append(asset_program_data)
            except Exception:
                logger.exception(f'Problem getting query program')

            asset_patch_dict = dict()
            try:
                for asset_patch_data in client_data.query(consts.QUERY_PATCH):
                    asset_id = asset_patch_data.get('ResourceID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_patch_dict:
                        asset_patch_dict[asset_id] = []
                    asset_patch_dict[asset_id].append(asset_patch_data)
            except Exception:
                logger.exception(f'Problem getting query patch')

            asset_bios_dict = dict()
            try:
                for asset_bios_data in client_data.query(consts.BIOS_QUERY):
                    asset_id = asset_bios_data.get('ResourceID')
                    if not asset_id:
                        continue
                    asset_bios_dict[asset_id] = asset_bios_data
            except Exception:
                logger.exception(f'Problem getting query bios')

            if not self._last_seen_timedelta:
                for device_raw in client_data.query(consts.SCCM_QUERY.format('')):
                    yield device_raw, asset_software_dict, asset_patch_dict, \
                        asset_program_dict, asset_bios_dict, asset_users_dict, asset_top_dict, asset_malware_dict
            else:
                for device_raw in client_data.query(consts.SCCM_QUERY.format(consts.LIMIT_SCCM_QUERY.format(self._last_seen_timedelta.total_seconds() / 3600))):
                    yield device_raw, asset_software_dict, asset_patch_dict,\
                        asset_program_dict, asset_bios_dict, asset_users_dict, asset_top_dict, asset_malware_dict
        finally:
            client_data.logout()

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
        for device_raw, asset_software_dict, asset_patch_dict, asset_program_dict, \
            asset_bios_dict, asset_users_dict, asset_top_dict, asset_malware_dict in\
                devices_raw_data:
            try:
                device_id = device_raw.get('Distinguished_Name0')
                if not device_id:
                    # In case of no AD distinguished name, at least we have the netbios name plus resource ID,
                    # both are not that good, but together they should make a good id.
                    device_id = (device_raw.get('Netbios_Name0') or '') + str(device_raw.get('ResourceID') or '')
                    if not device_id:
                        logger.error(f'Got a device with no distinguished name {device_raw}')
                        continue
                device = self._new_device_adapter()
                device.id = device_id
                try:
                    users_raw = asset_users_dict.get(device_raw.get('ResourceID'))
                    if users_raw and isinstance(users_raw, list):
                        device.last_used_users = [user_raw.get('UniqueUserName') for user_raw in users_raw
                                                  if user_raw.get('UniqueUserName')]
                except Exception:
                    logger.exception(f'Problem adding users to {device_raw}')
                device.resource_id = str(device_raw.get('ResourceID'))
                device.organizational_unit = get_organizational_units_from_dn(device_id)
                domain = device_raw.get('Full_Domain_Name0')
                device.hostname = device_raw.get('Netbios_Name0')
                if domain and device_raw.get('Netbios_Name0'):
                    device.hostname += '.' + domain
                    device.part_of_domain = True
                    device.domain = domain
                device.figure_os((device_raw.get('Caption0') or '') +
                                 (device_raw.get("Operating_System_Name_and0") or ''))
                mac_total = []
                ips_total = []
                for nic in (device_raw.get('Network Interfaces') or '').split(';'):
                    try:
                        if nic == '':
                            continue  # We dont need empty nics of course
                        mac, ips = nic.split('@')
                        mac = mac.strip()
                        ips = [ip.strip() for ip in ips.split(', ')]
                        mac_total.append(mac)
                        ips_total.extend(ips)
                        device.add_nic(mac, ips)
                    except Exception:
                        logger.exception(f'Problem with nic {nic}')
                for mac in (device_raw.get('Mac Addresses') or '').split(';'):
                    try:
                        mac = mac.strip()
                        if not mac or mac in mac_total:
                            continue
                        elif not mac_total:
                            mac_total.append(mac)
                            device.add_nic(mac, None)
                        else:
                            device.macs_no_ip.append(mac)
                            # Field stuff I saw pushed me to use
                    except Exception:
                        logger.warning(f"Caught weird NIC {mac} for device id {device.id}")
                        pass
                ips_empty_mac = []
                try:
                    ips_raw = (device_raw.get('IP Addresses') or '').split(';')
                    for ip_raw in ips_raw:
                        ips_empty_mac.extend(ip_raw.split(','))
                        ips_empty_mac = list(set([ip.strip() for ip in ips_empty_mac if ip.strip()]))
                        ips_empty_mac = list(set(ips_empty_mac) - set(ips_total))
                        device.add_nic(None, ips_empty_mac)
                except Exception:
                    logger.exception(f'Problem getting IP for {device_raw}')
                free_physical_memory = device_raw.get('FreePhysicalMemory0')
                device.free_physical_memory = float(free_physical_memory) if free_physical_memory else None
                total_physical_memory = device_raw.get('TotalPhysicalMemory0')
                device.total_physical_memory = float(device_raw.get('TotalPhysicalMemory0')) \
                    if total_physical_memory else None
                if total_physical_memory and free_physical_memory:
                    device.physical_memory_percentage = 100 * \
                        (1 - device.free_physical_memory / device.total_physical_memory)
                try:
                    if isinstance(asset_bios_dict.get(device_raw.get('ResourceID')), dict):
                        bios_data = asset_bios_dict.get(device_raw.get('ResourceID'))
                        device.bios_serial = bios_data.get('SerialNumber0')
                        device.device_manufacturer = bios_data.get('Manufacturer0')
                except Exception:
                    logger.exception(f'Problem getting bios data dor {device_raw}')
                device.sccm_type = device_raw.get('SystemType0')
                product_type_dict = {'1': 'WORKSTATION', '2': 'DOMAIN CONTROLLER', '3': 'SERVER'}
                device.sccm_product_type = product_type_dict.get(str(device_raw.get('ProductType0')))
                try:
                    if isinstance(asset_top_dict.get(device_raw.get('ResourceID')), dict):
                        top_data = asset_top_dict.get(device_raw.get('ResourceID'))
                        device.top_user = top_data.get('TopConsoleUser0')
                except Exception:
                    logger.exception(f'Problem getting top user data dor {device_raw}')

                try:
                    if isinstance(asset_malware_dict.get(device_raw.get('ResourceID')), dict):
                        malware_data = asset_malware_dict.get(device_raw.get('ResourceID'))
                        device.malware_engine_version = malware_data.get('EngineVersion')
                        device.malware_version = malware_data.get('Version')
                        device.malware_product_status = malware_data.get('ProductStatus')
                        device.malware_last_full_scan = parse_date(malware_data.get('LastFullScanDateTimeEnd'))
                        device.malware_last_quick_scan = parse_date(malware_data.get('LastQuickScanDateTimeEnd'))
                        device.malware_enabled = malware_data.get('Enabled')
                except Exception:
                    logger.exception(f'Problem getting malware data dor {device_raw}')
                device.device_model = device_raw.get('Model0')
                processes = device_raw.get('NumberOfProcesses0')
                device.number_of_processes = int(processes) if processes else None
                processors = device_raw.get('NumberOfProcessors0')
                device.total_number_of_physical_processors = int(processors) if processors else None
                device.current_logged_user = device_raw.get('UserName0') or device_raw.get('User_Name0')
                device.time_zone = device_raw.get('CurrentTimeZone0')
                device.boot_time = device_raw.get('LastBootUpTime0')
                last_seen = device_raw.get('Last Seen')
                try:
                    if last_seen:
                        device.last_seen = parse_date(last_seen)
                except Exception:
                    logger.exception(f'Can not parse last seen {last_seen}')
                try:
                    if isinstance(asset_software_dict.get(device_raw.get('ResourceID')), list):
                        for asset_data in asset_software_dict.get(device_raw.get('ResourceID')):
                            try:
                                device.add_installed_software(name=asset_data.get('ProductName0'),
                                                              version=asset_data.get('ProductVersion0'))
                            except Exception:
                                logger.exception(f'Problem adding asset {asset_data}')
                except Exception:
                    logger.exception(f'Problem adding software to {device_raw}')

                try:
                    if isinstance(asset_program_dict.get(device_raw.get('ResourceID')), list):
                        for asset_data in asset_program_dict.get(device_raw.get('ResourceID')):
                            try:
                                device.add_installed_software(name=asset_data.get('DisplayName0'),
                                                              version=asset_data.get('Version0'))
                            except Exception:
                                logger.exception(f'Problem adding asset {asset_data}')
                except Exception:
                    logger.exception(f'Problem adding program to {device_raw}')

                try:
                    if isinstance(asset_patch_dict.get(device_raw.get('ResourceID')), list):
                        for patch_data in asset_patch_dict.get(device_raw.get('ResourceID')):
                            try:
                                patch_description = patch_data.get('Description0') or ''
                                if patch_data.get('FixComments0'):
                                    patch_description += ' Hotfix Comments:' + patch_data.get('FixComments0')
                                if not patch_description:
                                    patch_description = None
                                installed_on = parse_date(patch_data.get('InstallDate0'))
                                device.add_security_patch(security_patch_id=patch_data.get('HotFixID0'),
                                                          patch_description=patch_description,
                                                          installed_on=installed_on)
                            except Exception:
                                logger.exception(f'Problem adding patch {patch_data}')
                except Exception:
                    logger.exception(f'Problem adding patch to {device_raw}')

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f"Problem with device: {device_raw}")

    def _correlation_cmds(self):
        logger.error("correlation_cmds is not implemented for sccm adapter")
        raise NotImplementedError("correlation_cmds is not implemented for sccm adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        logger.error("_parse_correlation_results is not implemented for sccm adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for sccm adapter")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
