import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.ad_entity import ADEntity
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_organizational_units_from_dn, get_exception_string, is_valid_ipv6
import sccm_adapter.consts as consts

logger = logging.getLogger(f'axonius.{__name__}')

DESKTOP_CHASIS_VALUE = ['3', '4', '6', '7', '15']
LAPTOP_CHASIS_VALUE = ['8', '9', '10', '21']
CHASIS_VALUE_FULL_DICT = {
    '1': 'Virtual Machine',
    '2': 'Blade Server',
    '3': 'Desktop',
    '4': 'Low-Profile Desktop',
    '5': 'Pizza Box',
    '6': 'Mini Tower',
    '7': 'Tower',
    '8': 'Portable',
    '9': 'Laptop',
    '10': 'Notebook',
    '11': 'Hand Held',
    '12': 'Docking Station',
    '13': 'All-in-One',
    '14': 'Sub Notebook',
    '15': 'Space Saving Chassis',
    '16': 'Ultra Small Form Factor',
    '17': 'Server Tower Chassis',
    '18': 'Mobile Device in Docking Station',
    '19': 'Sub-Chassis',
    '20': 'Bus-Expansion Chassis',
    '21': 'Peripheral Chassis',
    '22': 'Storage Chassis',
    '23': 'Rack Mount Unit',
    '24': 'Sealed-Case PC',
}


class SccmVm(SmartJsonClass):
    vm_dns_name = Field(str, 'VM DNS Name')
    vm_ip = Field(str, 'VM IP Address')
    vm_state = Field(str, 'VM State')
    vm_name = Field(str, 'VM Name')
    vm_path = Field(str, 'VM Path')
    vm_type = Field(str, 'VM Type')
    vm_timestamp = Field(str, 'VM Timestamp')


class SccmAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter, ADEntity):
        resource_id = Field(str, 'Resource ID')
        sccm_server = Field(str, 'SCCM Server')
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
        desktop_or_laptop = Field(str, 'Desktop Or Laptop', enum=['Desktop', 'Laptop'])
        chasis_value = Field(str, 'Chasis Value')
        sccm_vms = ListField(SccmVm, 'SCCM VMs')
        owner = Field(str, 'Owner')
        department = Field(str, 'Department')
        purpose = Field(str, 'Purpose')
        tpm_is_activated = Field(bool, 'TPM Is Activated')
        tpm_is_enabled = Field(bool, 'TPM Is Enabled')
        tpm_is_owned = Field(bool, 'TPM Is Owned')

        def add_sccm_vm(self, **kwargs):
            try:
                self.sccm_vms.append(SccmVm(**kwargs))
            except Exception:
                logger.exception(f'Problem adding sccm vm')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.SCCM_HOST]

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(
                database=client_config[consts.SCCM_DATABASE],
                server=client_config[consts.SCCM_HOST],
                port=client_config.get(consts.SCCM_PORT) or consts.DEFAULT_SCCM_PORT,
                devices_paging=self.__devices_fetched_at_a_time,
            )
            connection.set_credentials(username=client_config[consts.USER], password=client_config[consts.PASSWORD])
            with connection:
                for device_raw in connection.query('select ResourceID from v_R_SYSTEM'):
                    break
            return connection
        except Exception as err:
            message = (
                f"Error connecting to client host: {str(client_config[consts.SCCM_HOST])}  "
                f"database: {str(client_config[consts.SCCM_DATABASE])}"
            )
            logger.exception(message)
            if 'permission was denied' in str(repr(err)).lower():
                raise ClientConnectionException(f'Error connecting to SCCM: {str(err)}')
            else:
                raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:

            nics_dict = dict()
            try:
                for nic_data in client_data.query(consts.NICS_QUERY):
                    asset_id = nic_data.get('ResourceID')
                    if not asset_id:
                        continue
                    if asset_id not in nics_dict:
                        nics_dict[asset_id] = []
                    nics_dict[asset_id].append(nic_data)
            except Exception:
                logger.exception(f'Problem getting nics dict')

            clients_dict = dict()
            try:
                for clients_data in client_data.query(consts.CLIENT_SUMMARY_QUERY):
                    asset_id = clients_data.get('ResourceID')
                    if not asset_id:
                        continue
                    clients_dict[asset_id] = clients_data
            except Exception:
                logger.exception(f'Problem getting clietns data')

            os_dict = dict()
            try:
                for os_data in client_data.query(consts.OS_DATA_QUERY):
                    asset_id = os_data.get('ResourceID')
                    if not asset_id:
                        continue
                    os_dict[asset_id] = os_data
            except Exception:
                logger.exception(f'Problem getting os data')

            computer_dict = dict()
            try:
                for computer_data in client_data.query(consts.COMPUTER_SYSTEM_QUERY):
                    asset_id = computer_data.get('ResourceID')
                    if not asset_id:
                        continue
                    computer_dict[asset_id] = computer_data
            except Exception:
                logger.exception(f'Problem getting computer data')

            tpm_dict = dict()
            try:
                for tpm_data in client_data.query(consts.TPM_QUERY):
                    asset_id = tpm_data.get('ResourceID')
                    if not asset_id:
                        continue
                    tpm_dict[asset_id] = tpm_data
            except Exception:
                logger.exception(f'Problem getting tpm')

            owner_dict = dict()
            try:
                for owner_data in client_data.query(consts.OWNER_QUERY):
                    asset_id = owner_data.get('MachineID')
                    if not asset_id:
                        continue
                    owner_dict[asset_id] = owner_data
            except Exception:
                logger.exception(f'Problem getting owner')

            asset_encryption_dict = dict()
            try:
                for asset_encryption_data in client_data.query(consts.ENCRYPTION_QUERY):
                    asset_id = asset_encryption_data.get('ResourceID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_encryption_dict:
                        asset_encryption_dict[asset_id] = []
                    asset_encryption_dict[asset_id].append(asset_encryption_data)
            except Exception:
                logger.exception(f'Problem getting query asset_encryption_dict')

            asset_vm_dict = dict()
            try:
                for asset_vm_data in client_data.query(consts.VM_QUERY):
                    asset_id = asset_vm_data.get('ResourceID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_vm_dict:
                        asset_vm_dict[asset_id] = []
                    asset_vm_dict[asset_id].append(asset_vm_data)
            except Exception:
                logger.exception(f'Problem getting vm')

            asset_chasis_dict = dict()
            try:
                for asset_chasis_data in client_data.query(consts.CHASIS_QUERY):
                    asset_id = asset_chasis_data.get('ResourceID')
                    if not asset_id:
                        continue
                    asset_chasis_dict[asset_id] = asset_chasis_data
            except Exception:
                logger.exception(f'Problem getting chasis')

            asset_lenovo_dict = dict()
            try:
                for asset_lenovo_data in client_data.query(consts.LENOVO_QUERY):
                    asset_id = asset_lenovo_data.get('ResourceID')
                    if not asset_id:
                        continue
                    asset_lenovo_dict[asset_id] = asset_lenovo_data
            except Exception:
                logger.exception(f'Problem getting lenovo')

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

            for device_raw in client_data.query(consts.SCCM_MAIN_QUERY):
                yield device_raw, client_data.server, asset_software_dict, asset_patch_dict, asset_program_dict, \
                    asset_bios_dict, asset_users_dict, asset_top_dict, asset_malware_dict, \
                    asset_lenovo_dict, asset_chasis_dict, asset_encryption_dict,\
                    asset_vm_dict, owner_dict, tpm_dict, computer_dict, clients_dict, os_dict, nics_dict

    def _clients_schema(self):
        return {
            "items": [
                {"name": consts.SCCM_HOST, "title": "SCCM/MSSQL Server", "type": "string"},
                {"name": consts.SCCM_PORT, "title": "Port", "type": "integer", "default": consts.DEFAULT_SCCM_PORT},
                {"name": consts.SCCM_DATABASE, "title": "Database", "type": "string"},
                {"name": consts.USER, "title": "User Name", "type": "string"},
                {"name": consts.PASSWORD, "title": "Password", "type": "string", "format": "password"},
            ],
            "required": [consts.SCCM_HOST, consts.USER, consts.PASSWORD, consts.SCCM_DATABASE],
            "type": "array",
        }

    def _parse_raw_data(self, devices_raw_data):
        for (
            device_raw,
            sccm_server,
            asset_software_dict,
            asset_patch_dict,
            asset_program_dict,
            asset_bios_dict,
            asset_users_dict,
            asset_top_dict,
            asset_malware_dict,
            asset_lenovo_dict,
            asset_chasis_dict,
            asset_encryption_dict,
            asset_vm_dict,
            owner_dict,
            tpm_dict,
            computer_dict,
            clients_dict,
            os_dict, nics_dict
        ) in devices_raw_data:
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
                device.sccm_server = sccm_server
                os_data = os_dict.get(device_raw.get('ResourceID'))
                if not isinstance(os_data, dict):
                    os_data = {}
                computer_data = computer_dict.get(device_raw.get('ResourceID'))
                if not isinstance(computer_data, dict):
                    computer_data = {}
                try:
                    users_raw = asset_users_dict.get(device_raw.get('ResourceID'))
                    if users_raw and isinstance(users_raw, list):
                        device.last_used_users = [
                            user_raw.get('UniqueUserName') for user_raw in users_raw if user_raw.get('UniqueUserName')
                        ]
                except Exception:
                    logger.exception(f'Problem adding users to {device_raw}')

                try:
                    encryptions_raw = asset_encryption_dict.get(device_raw.get('ResourceID'))
                    if encryptions_raw and isinstance(encryptions_raw, list):
                        for drive_enc_data in encryptions_raw:
                            try:
                                is_encrypted = None
                                if str(drive_enc_data.get('ProtectionStatus0')) == '1':
                                    is_encrypted = True
                                elif str(drive_enc_data.get('ProtectionStatus0')) == '0':
                                    is_encrypted = False
                                if drive_enc_data.get('DriveLetter0'):
                                    device.add_hd(path=drive_enc_data.get('DriveLetter0'), is_encrypted=is_encrypted)
                            except Exception:
                                logger.exception(f'Problem getting enc data for {drive_enc_data}')
                except Exception:
                    logger.exception(f'Problem adding users to {device_raw}')
                device.resource_id = str(device_raw.get('ResourceID'))
                device.organizational_unit = get_organizational_units_from_dn(device_id)
                domain = device_raw.get('Full_Domain_Name0')
                device.add_agent_version(version=device_raw.get('Client_Version0'),
                                         agent=AGENT_NAMES.sccm)
                device.hostname = device_raw.get('Netbios_Name0')
                if domain and device_raw.get('Netbios_Name0'):
                    device.hostname += '.' + domain
                    device.part_of_domain = True
                    device.domain = domain
                device.figure_os(
                    (computer_data.get('Caption0') or '') + (device_raw.get("Operating_System_Name_and0") or '')
                )

                mac_total = []
                ips_total = []
                for nic in (device_raw.get('Network Interfaces') or '').split(';'):
                    try:
                        if nic == '':
                            continue  # We dont need empty nics of course
                        mac, ips = nic.split('@')
                        mac = mac.strip()
                        ips = [ip.strip() for ip in ips.split(', ')]
                        if self.__exclude_ipv6:
                            ips = [ip for ip in ips if not is_valid_ipv6(ip)]
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
                        if self.__exclude_ipv6:
                            ips_empty_mac = [ip for ip in ips_empty_mac if not is_valid_ipv6(ip)]
                        device.add_nic(None, ips_empty_mac)
                except Exception:
                    logger.exception(f'Problem getting IP for {device_raw}')
                try:
                    free_physical_memory = device_raw.get('FreePhysicalMemory0')
                    device.free_physical_memory = (
                        float(free_physical_memory) / (1024 ** 2) if free_physical_memory else None
                    )
                    total_physical_memory = device_raw.get('TotalPhysicalMemory0')
                    device.total_physical_memory = (
                        float(device_raw.get('TotalPhysicalMemory0')) / (1024 ** 2) if total_physical_memory else None
                    )
                    if total_physical_memory and free_physical_memory:
                        device.physical_memory_percentage = 100 * (
                            1 - device.free_physical_memory / device.total_physical_memory
                        )
                except Exception:
                    logger.exception(f'problem adding memory stuff to {device_raw}')
                device_manufacturer = None
                try:
                    if isinstance(asset_bios_dict.get(device_raw.get('ResourceID')), dict):
                        bios_data = asset_bios_dict.get(device_raw.get('ResourceID'))
                        device.bios_serial = bios_data.get('SerialNumber0')
                        device_manufacturer = bios_data.get('Manufacturer0')
                        device.device_manufacturer = device_manufacturer
                except Exception:
                    logger.exception(f'Problem getting bios data dor {device_raw}')
                device.sccm_type = computer_data.get('SystemType0')
                product_type_dict = {'1': 'WORKSTATION', '2': 'DOMAIN CONTROLLER', '3': 'SERVER'}
                device.sccm_product_type = product_type_dict.get(str(device_raw.get('ProductType0')))
                try:
                    if isinstance(asset_top_dict.get(device_raw.get('ResourceID')), dict):
                        top_data = asset_top_dict.get(device_raw.get('ResourceID'))
                        device.top_user = top_data.get('TopConsoleUser0')
                except Exception:
                    logger.exception(f'Problem getting top user data dor {device_raw}')

                try:
                    if isinstance(nics_dict.get(device_raw.get('ResourceID')), list):
                        for nic_data in nics_dict.get(device_raw.get('ResourceID')):
                            try:
                                mac = nic_data.get('MACAddress0')
                                ips = nic_data.get('IPAddress0')
                                if mac:
                                    mac = mac.strip()
                                else:
                                    mac = None
                                if ips:
                                    ips = [ip.strip() for ip in ips.split(',')]
                                else:
                                    ips = []
                                if self.__exclude_ipv6:
                                    ips = [ip for ip in ips if not is_valid_ipv6(ip)]
                                if ips:
                                    device.add_nic(mac, ips)
                                elif mac:
                                    device.macs_no_ip.append(mac)
                            except Exception:
                                logger.exception(f'Problem with nic data {nic_data}')
                except Exception:
                    logger.exception(f'Problem getting vm data dor {device_raw}')

                try:
                    if isinstance(asset_vm_dict.get(device_raw.get('ResourceID')), list):
                        for vm_data in asset_vm_dict.get(device_raw.get('ResourceID')):
                            try:
                                vm_dns_name = vm_data.get('DNSName0')
                                vm_ip = vm_data.get('IPAddress0')
                                vm_state = vm_data.get('State0')
                                vm_name = vm_data.get('VMName0')
                                vm_path = vm_data.get('Path0')
                                vm_type = vm_data.get('Type0')
                                vm_timestamp = vm_data.get('TimeStamp')
                                device.add_sccm_vm(vm_dns_name=vm_dns_name,
                                                   vm_ip=vm_ip,
                                                   vm_state=vm_state,
                                                   vm_name=vm_name,
                                                   vm_path=vm_path,
                                                   vm_type=vm_type,
                                                   vm_timestamp=vm_timestamp)
                            except Exception:
                                logger.exception(f'Problem with vm_data {vm_data}')
                except Exception:
                    logger.exception(f'Problem getting vm data dor {device_raw}')

                try:
                    if isinstance(tpm_dict.get(device_raw.get('ResourceID')), dict):
                        tpm_data = tpm_dict.get(device_raw.get('ResourceID'))
                        device.tpm_is_activated = tpm_data.get('IsActivated_InitialValue0') == 1
                        device.tpm_is_enabled = tpm_data.get('IsEnabled_InitialValue0') == 1
                        device.tpm_is_owned = tpm_data.get('IsOwned_InitialValue0') == 1
                except Exception:
                    logger.exception(f'Problem getting tpm data dor {device_raw}')
                try:
                    if isinstance(owner_dict.get(device_raw.get('ResourceID')), dict):
                        owner_data = owner_dict.get(device_raw.get('ResourceID'))
                        device.owner = owner_data.get('Owner00')
                        device.department = owner_data.get('Department00')
                        device.purpose = owner_data.get('Purpose00')
                except Exception:
                    logger.exception(f'Problem getting owner data dor {device_raw}')

                try:
                    if isinstance(clients_dict.get(device_raw.get('ResourceID')), dict):
                        client_data = clients_dict.get(device_raw.get('ResourceID'))
                        device.last_seen = parse_date(client_data.get('LastActiveTime'))
                except Exception:
                    logger.exception(f'Problem getting last seen data dor {device_raw}')

                try:
                    if isinstance(asset_chasis_dict.get(device_raw.get('ResourceID')), dict):
                        chasis_data = asset_chasis_dict.get(device_raw.get('ResourceID'))
                        chasis_types = chasis_data.get('ChassisTypes0')
                        if chasis_types and isinstance(chasis_types, str):
                            device.chasis_value = CHASIS_VALUE_FULL_DICT.get(chasis_types)
                        if chasis_types and str(chasis_types) in DESKTOP_CHASIS_VALUE:
                            device.desktop_or_laptop = 'Desktop'
                        elif chasis_types and str(chasis_types) in LAPTOP_CHASIS_VALUE:
                            device.desktop_or_laptop = 'Laptop'
                except Exception:
                    logger.exception(f'Problem getting chasis data dor {device_raw}')
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
                try:
                    if not device_manufacturer or 'LENOVO' not in device_manufacturer.upper():
                        device.device_model = computer_data.get('Model0')
                    elif isinstance(asset_lenovo_dict.get(device_raw.get('ResourceID')), dict):
                        device.device_model = asset_lenovo_dict.get(device_raw.get('ResourceID')).get('Version0')
                except Exception:
                    logger.exception(f'Problem getting model for {device_raw}')
                processes = computer_data.get('NumberOfProcesses0')
                device.number_of_processes = int(processes) if processes else None
                processors = computer_data.get('NumberOfProcessors0')
                device.total_number_of_physical_processors = int(processors) if processors else None
                device.current_logged_user = computer_data.get('UserName0') or device_raw.get('User_Name0')
                device.time_zone = computer_data.get('CurrentTimeZone0')
                if os_data.get('LastBootUpTime0'):
                    device.set_boot_time(boot_time=os_data.get('LastBootUpTime0'))

                try:
                    if isinstance(asset_software_dict.get(device_raw.get('ResourceID')), list):
                        for asset_data in asset_software_dict.get(device_raw.get('ResourceID')):
                            try:
                                device.add_installed_software(
                                    name=asset_data.get('ProductName0'), version=asset_data.get('ProductVersion0')
                                )
                            except Exception:
                                logger.exception(f'Problem adding asset {asset_data}')
                except Exception:
                    logger.exception(f'Problem adding software to {device_raw}')

                try:
                    if isinstance(asset_program_dict.get(device_raw.get('ResourceID')), list):
                        for asset_data in asset_program_dict.get(device_raw.get('ResourceID')):
                            try:
                                device.add_installed_software(
                                    name=asset_data.get('DisplayName0'), version=asset_data.get('Version0')
                                )
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
                                device.add_security_patch(
                                    security_patch_id=patch_data.get('HotFixID0'),
                                    patch_description=patch_description,
                                    installed_on=installed_on,
                                )
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

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    'name': 'exclude_ipv6',
                    'title': 'Exclude IPv6 addresses',
                    'type': 'bool'
                },
                {
                    'name': 'devices_fetched_at_a_time',
                    'type': 'integer',
                    'title': 'SQL pagination'
                }
            ],
            "required": [],
            "pretty_name": "SCCM Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'exclude_ipv6': False,
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__exclude_ipv6 = config['exclude_ipv6']
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
