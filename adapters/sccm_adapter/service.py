import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.ad_entity import ADEntity
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES, get_settings_cached
from axonius.multiprocess.multiprocess import concurrent_multiprocess_yield
from axonius.utils.network.sockets import test_reachability_tcp
from axonius.utils.parsing import is_domain_valid
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_organizational_units_from_dn,\
    get_exception_string, is_valid_ipv6
import sccm_adapter.consts as consts
from sccm_adapter.parse import sccm_query_devices_by_client, _create_sccm_client_connection

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


class DriverData(SmartJsonClass):
    driver_name = Field(str, 'Driver Name')
    driver_description = Field(str, 'Driver Description')
    driver_version = Field(str, 'Driver Version')
    driver_provider = Field(str, 'Driver Provider')
    driver_date = Field(datetime.datetime, 'Driver Date')


class SccmVm(SmartJsonClass):
    vm_dns_name = Field(str, 'VM DNS Name')
    vm_ip = Field(str, 'VM IP Address')
    vm_state = Field(str, 'VM State')
    vm_name = Field(str, 'VM Name')
    vm_path = Field(str, 'VM Path')
    vm_type = Field(str, 'VM Type')
    vm_timestamp = Field(str, 'VM Timestamp')


class SccmGroupData(SmartJsonClass):
    group_name = Field(str, 'Group Name')
    groups = ListField(str, 'Groups')
    local_users = ListField(str, 'Local Users')
    doomain_users = ListField(str, 'Domain Users')


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
        department = Field(str, 'Department')
        purpose = Field(str, 'Purpose')
        tpm_is_activated = Field(bool, 'TPM Is Activated')
        tpm_is_enabled = Field(bool, 'TPM Is Enabled')
        tpm_is_owned = Field(bool, 'TPM Is Owned')
        collections = ListField(str, 'Collections')
        applications = ListField(str, 'Applications')
        compliance_status = Field(str, 'Compliance Status')
        drivers_data = ListField(DriverData, 'Drivers Data')
        network_drivers_data = ListField(DriverData, 'Network Drivers Data')
        bios_release_date = Field(datetime.datetime, 'Bios Release Date')
        sccm_groups_data = ListField(SccmGroupData, 'Groups Data')
        is_online = Field(bool, 'Is Online')
        is_on_internet = Field(bool, 'Is On Internet')
        last_online_time = Field(datetime.datetime, 'Last Online Time')
        last_offline_time = Field(datetime.datetime, 'Last Offline Time')
        access_mp = Field(str, 'Access MP')
        guard_compliance_state = Field(str, 'Credential Guard Compliance State')

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
        return test_reachability_tcp(
            client_config.get('server'),
            client_config.get('port') or consts.DEFAULT_SCCM_PORT
        )

    def _connect_client(self, client_config):
        try:
            connection = _create_sccm_client_connection(client_config, self.__devices_fetched_at_a_time)
            with connection:
                for _ in connection.query('select ResourceID from v_R_SYSTEM'):
                    break
            return client_config
        except Exception as err:
            message = (
                f"Error connecting to client host: {str(client_config[consts.SCCM_HOST])}  "
                f"database: {str(client_config[consts.SCCM_DATABASE])}"
            )
            logger.exception(message)
            if 'permission was denied' in str(repr(err)).lower():
                raise ClientConnectionException(f'Error connecting to SCCM: {str(err)}')
            else:
                raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    def _refetch_device(self, client_id, client_config, device_id):
        for device in self._parse_raw_data(
                sccm_query_devices_by_client(
                    client_config,
                    self.__devices_fetched_at_a_time,
                    device_id
                )
        ):
            return device

    def _query_devices_by_client(self, client_name, client_data):
        _ = (yield from concurrent_multiprocess_yield(
            [
                (
                    sccm_query_devices_by_client,
                    (
                        client_data,
                        self.__devices_fetched_at_a_time,
                        None
                    ),
                    {}
                )
            ],
            1
        ))
        # To restore original method:
        # yield from sccm_query_devices_by_client(client_data, self.__devices_fetched_at_a_time, None)

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
        for device_raw in devices_raw_data:
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
                device.sccm_server = device_raw['sccm_server']
                try:
                    device.ad_distinguished_name = device_raw.get('Distinguished_Name0')
                except Exception:
                    pass
                os_data = device_raw['os_data']
                if not isinstance(os_data, dict):
                    os_data = {}
                computer_data = device_raw['computer_data']
                if not isinstance(computer_data, dict):
                    computer_data = {}
                try:
                    users_raw = device_raw['users_raw']
                    if users_raw and isinstance(users_raw, list):
                        device.last_used_users = [
                            user_raw.get('UniqueUserName') for user_raw in users_raw if user_raw.get('UniqueUserName')
                        ]
                except Exception:
                    logger.exception(f'Problem adding users to {device_raw}')
                device.collections = device_raw['collections_list']
                device.applications = device_raw['applications_list']
                try:
                    encryptions_raw = device_raw['encryptions_raw']
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
                device.ad_site_name = device_raw.get('AD_Site_Name0')
                domain = device_raw.get('Full_Domain_Name0')
                if domain:
                    device.part_of_domain = True
                    device.domain = domain
                device.add_agent_version(version=device_raw.get('Client_Version0'),
                                         agent=AGENT_NAMES.sccm)
                if self.__machine_domain_whitelist and domain and domain.lower() not in self.__machine_domain_whitelist:
                    continue

                device_full_hostname = device_raw.get('Netbios_Name0')
                if device_full_hostname == 'Unknown':
                    continue
                if device_full_hostname:
                    if domain:
                        device_full_hostname += '.' + domain
                    device.hostname = device_full_hostname
                    device_id += f'${device.hostname}'

                device.id = device_id
                try:
                    build = device_raw.get('BuildExt') or device_raw.get('Build01')
                    device.figure_os((device_raw.get('operatingSystem0') or '') + ' ' +
                                     (device_raw.get('Operating_System_Name_and0') or '') + ' ' + (build or ''))
                    device.os.build = build
                except Exception:
                    pass
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
                    total_physical_memory = device_raw.get('TotalPhysicalMemory0')\
                        or device_raw['ram_data']
                    device.total_physical_memory = (
                        float(total_physical_memory) / (1024 ** 1) if total_physical_memory else None
                    )
                    if total_physical_memory and free_physical_memory:
                        device.physical_memory_percentage = 100 * (
                            1 - device.free_physical_memory / device.total_physical_memory
                        )
                except Exception:
                    logger.exception(f'problem adding memory stuff to {device_raw}')
                device_manufacturer = None

                try:
                    if isinstance(device_raw['guard_compliance_data'], dict):
                        guard_compliance_data = device_raw['guard_compliance_data']
                        if not isinstance(guard_compliance_data, dict):
                            guard_compliance_data = {}
                        guard_compliance_state = guard_compliance_data.get('ComplianceState')
                        if isinstance(guard_compliance_state, int):
                            guard_compliance_state = str(guard_compliance_state)
                        if guard_compliance_state == '1':
                            device.guard_compliance_state = 'Compliant'
                        elif guard_compliance_state == '3':
                            device.guard_compliance_state = 'Non-Compliant'
                        elif guard_compliance_state == '4':
                            device.guard_compliance_state = 'Not-Eligible'
                except Exception:
                    logger.exception(f'Problem getting guard compliance data data dor {device_raw}')
                try:
                    if isinstance(device_raw['online_data'], dict):
                        online_data = device_raw['online_data']
                        if not isinstance(online_data, dict):
                            online_data = {}
                        device.is_online = online_data.get('CNIsOnline')\
                            if isinstance(online_data.get('CNIsOnline'), bool) else None
                        device.last_online_time = parse_date(online_data.get('CNLastOnlineTime'))
                        device.last_offline_time = parse_date(online_data.get('CNLastOfflineTime'))
                        device.access_mp = online_data.get('CNAccessMP')
                        device.is_on_internet = online_data.get('CNIsOnInternet') \
                            if isinstance(online_data.get('CNIsOnInternet'), bool) else None
                except Exception:
                    logger.exception(f'Problem getting online data dor {device_raw}')
                try:
                    if isinstance(device_raw['bios_data'], dict):
                        bios_data = device_raw['bios_data']
                        device.bios_serial = bios_data.get('SerialNumber0')
                        device_manufacturer = bios_data.get('Manufacturer0')
                        device.device_manufacturer = device_manufacturer
                        device.bios_release_date = parse_date(bios_data.get('ReleaseDate0'))
                except Exception:
                    logger.exception(f'Problem getting bios data dor {device_raw}')
                try:
                    if isinstance(device_raw['compliance_data'], dict):
                        compliance_data = device_raw['compliance_data']
                        device.compliance_status = compliance_data.get('Status')
                except Exception:
                    logger.exception(f'Problem getting bios data dor {device_raw}')
                device.sccm_type = computer_data.get('SystemType0')
                product_type_dict = {'1': 'WORKSTATION', '2': 'DOMAIN CONTROLLER', '3': 'SERVER'}
                device.sccm_product_type = product_type_dict.get(str(device_raw.get('ProductType0')))
                try:
                    if isinstance(device_raw['top_data'], dict):
                        top_data = device_raw['top_data']
                        device.top_user = top_data.get('TopConsoleUser0')
                except Exception:
                    logger.exception(f'Problem getting top user data dor {device_raw}')

                try:
                    if isinstance(device_raw['svc_data'], list):
                        for svc_data in device_raw['svc_data']:
                            try:
                                display_name = svc_data.get('DisplayName0')
                                path_name = svc_data.get('PathName0')
                                service_type = svc_data.get('ServiceType0')
                                start_mode = svc_data.get('StartMode0')
                                state = svc_data.get('State0')
                                device.add_service(display_name=display_name,
                                                   path_name=path_name,
                                                   start_mode=start_mode,
                                                   status=state,
                                                   service_type=service_type)
                            except Exception:
                                logger.exception(f'Problem with service data {svc_data}')
                except Exception:
                    logger.exception(f'Problem getting services data dor {device_raw}')
                try:
                    if isinstance(device_raw['disks_data'], list):
                        for disks_data in device_raw['disks_data']:
                            try:
                                free_space = disks_data.get('FreeSpace0')
                                size_space = disks_data.get('Size0')
                                hd_name = disks_data.get('DeviceID0')
                                device.add_hd(total_size=size_space, free_size=free_space, device=hd_name)
                            except Exception:
                                logger.exception(f'Problem with share data {disks_data}')
                except Exception:
                    logger.exception(f'Problem getting disks data dor {device_raw}')
                try:
                    if isinstance(device_raw['share_data'], list):
                        for share_data in device_raw['share_data']:
                            try:
                                share_path = share_data.get('Path0')
                                share_name = share_data.get('Name0')
                                share_description = share_data.get('Description0')
                                share_status = share_data.get('Status0')
                                device.add_share(path=share_path,
                                                 description=share_description,
                                                 status=share_status,
                                                 name=share_name)
                            except Exception:
                                logger.exception(f'Problem with share data {share_data}')
                except Exception:
                    logger.exception(f'Problem getting shares data dor {device_raw}')

                try:
                    if isinstance(device_raw['network_drivers_data'], list):
                        for network_drivers_data in device_raw['network_drivers_data']:
                            try:
                                driver_name = network_drivers_data.get('name0')
                                driver_description = network_drivers_data.get('DriverDesc0')
                                driver_version = network_drivers_data.get('DriverVersion0')
                                driver_provider = network_drivers_data.get('ProviderName0')
                                driver_date = parse_date(network_drivers_data.get('DriverDate0'))
                                device.network_drivers_data.append(DriverData(driver_name=driver_name,
                                                                              driver_description=driver_description,
                                                                              driver_version=driver_version,
                                                                              driver_provider=driver_provider,
                                                                              driver_date=driver_date))

                            except Exception:
                                logger.exception(f'Problem with drivers data {network_drivers_data}')
                except Exception:
                    logger.exception(f'Problem getting drivers data dor {device_raw}')

                try:
                    if isinstance(device_raw['drivers_data'], list):
                        for drivers_data in device_raw['drivers_data']:
                            try:
                                driver_name = drivers_data.get('Name0')
                                driver_description = drivers_data.get('Description0')
                                driver_version = drivers_data.get('DriverVersion0')
                                device.drivers_data.append(DriverData(driver_name=driver_name,
                                                                      driver_description=driver_description,
                                                                      driver_version=driver_version))

                            except Exception:
                                logger.exception(f'Problem with drivers data {drivers_data}')
                except Exception:
                    logger.exception(f'Problem getting drivers data dor {device_raw}')

                try:
                    device.local_admins = []
                    device.local_admins_domain_users = []
                    device.local_admins_local_users = []
                    device.local_admins_groups = []
                    device.local_admins_users = []
                    if isinstance(device_raw['local_admin_data'], list):
                        for local_admin_data in device_raw['local_admin_data']:
                            try:
                                user_local_admin = local_admin_data.get('account0')
                                domain_local_admin = local_admin_data.get('domain0')
                                admin_type = None
                                if local_admin_data.get('Category0') == 'UserAccount':
                                    admin_type = 'Admin User'
                                if local_admin_data.get('Category0') == 'Group':
                                    admin_type = 'Group Membership'
                                if is_domain_valid(domain_local_admin):
                                    if '.' not in domain_local_admin:
                                        user_local_admin = f'{domain_local_admin}\\{user_local_admin}'
                                    else:
                                        user_local_admin = f'{user_local_admin}@{domain_local_admin}'
                                    try:
                                        if admin_type == 'Admin User':
                                            hostname_start_lower = device_full_hostname.split('.')[0].lower()
                                            domain_start_lower = domain_local_admin.split('.')[0].lower()
                                            if hostname_start_lower != domain_start_lower:
                                                device.local_admins_domain_users.append(
                                                    local_admin_data.get('account0'))
                                            else:
                                                device.local_admins_local_users.append(local_admin_data.get('account0'))
                                    except Exception:
                                        pass
                                device.add_local_admin(admin_name=user_local_admin, admin_type=admin_type)
                            except Exception:
                                logger.exception(f'Problem with local admin data {local_admin_data}')
                except Exception:
                    logger.exception(f'Problem getting vm data dor {device_raw}')
                try:
                    groups_dict = dict()
                    if isinstance(device_raw['group_data'], list):
                        for group_data in device_raw['group_data']:
                            try:
                                account_name = group_data.get('account0')
                                domain_name = group_data.get('domain0')
                                category = group_data.get('Category0')
                                group_name = group_data.get('name0')
                                if group_name:
                                    if group_name not in groups_dict:
                                        groups_dict[group_name] = []
                                    groups_dict[group_name].append((account_name, domain_name, category))
                            except Exception:
                                logger.exception(f'Problem with group raw {group_data}')
                    for group_name, group_data in groups_dict.items():
                        group_groups = []
                        group_domain_users = []
                        group_local_users = []
                        for (account_name, domain_name, category) in group_data:
                            if category == 'UserAccount':
                                hostname_start_lower = device_full_hostname.split('.')[0].lower()
                                domain_start_lower = domain_name.split('.')[0].lower()
                                if hostname_start_lower != domain_start_lower:
                                    group_domain_users.append(account_name)
                                else:
                                    group_local_users.append(account_name)
                            elif category == 'Group':
                                group_groups.append(account_name)
                        device.sccm_groups_data.append(SccmGroupData(groups=group_groups,
                                                                     local_users=group_local_users,
                                                                     doomain_users=group_domain_users,
                                                                     group_name=group_name))
                except Exception:
                    logger.exception(f'Problem getting groups data')
                try:
                    if isinstance(device_raw['nic_data'], list):
                        for nic_data in device_raw['nic_data']:
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
                    if isinstance(device_raw['vm_data'], list):
                        for vm_data in device_raw['vm_data']:
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
                    if isinstance(device_raw['tpm_data'], dict):
                        tpm_data = device_raw['tpm_data']
                        device.tpm_is_activated = tpm_data.get('IsActivated_InitialValue0') == 1
                        device.tpm_is_enabled = tpm_data.get('IsEnabled_InitialValue0') == 1
                        device.tpm_is_owned = tpm_data.get('IsOwned_InitialValue0') == 1
                except Exception:
                    logger.exception(f'Problem getting tpm data dor {device_raw}')
                try:
                    if isinstance(device_raw['owner_data'], dict):
                        owner_data = device_raw['owner_data']
                        device.owner = owner_data.get('Owner00')
                        device.department = owner_data.get('Department00')
                        device.purpose = owner_data.get('Purpose00')
                except Exception:
                    logger.exception(f'Problem getting owner data dor {device_raw}')
                try:
                    if isinstance(device_raw['client_data'], dict):
                        client_data = device_raw['client_data']
                        last_seen = parse_date(client_data.get('LastActiveTime'))
                        if self.__drop_no_last_seen is True and not last_seen:
                            continue
                        device.last_seen = last_seen
                    elif self.__drop_no_last_seen is True:
                        continue
                except Exception:
                    logger.exception(f'Problem getting last seen data dor {device_raw}')
                try:
                    if isinstance(device_raw['mem_data'], dict):
                        mem_data = device_raw['mem_data']
                        if mem_data.get('TotalPhysicalMemory0'):
                            device.total_physical_memory = float(mem_data.get('TotalPhysicalMemory0')) / (1024.0 ** 2)
                except Exception:
                    logger.exception(f'Problem getting mem data dor {device_raw}')
                try:
                    if isinstance(device_raw['chasis_data'], dict):
                        chasis_data = device_raw['chasis_data']
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
                    if isinstance(device_raw['malware_data'], dict):
                        malware_data = device_raw['malware_data']
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
                    elif isinstance(device_raw['lenovo_data'], dict):
                        device.device_model = device_raw['lenovo_data'].get('Version0')
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
                    if isinstance(device_raw['new_sw_data'], list):
                        for new_asset_data in device_raw['new_sw_data']:
                            try:
                                path = None
                                try:
                                    file_data = new_asset_data.get('file_data')
                                    if not isinstance(file_data, dict):
                                        file_data = {}
                                    path = file_data.get('FilePath') or ''
                                    path += file_data.get('FileName') or ''
                                    if not path:
                                        path = None
                                except Exception:
                                    logger.warning(f'Problem with file data {new_asset_data}', exc_info=True)

                                if get_settings_cached()['should_populate_heavy_fields']:
                                    source_ais = 'SCCM SoftwareProduct Table'
                                    path_ais = path
                                else:
                                    source_ais = None
                                    path_ais = None

                                device.add_installed_software(
                                    name=new_asset_data.get('ProductName'),
                                    version=new_asset_data.get('ProductVersion'),
                                    vendor=new_asset_data.get('CompanyName'),
                                    source=source_ais,
                                    path=path_ais
                                )
                            except Exception:
                                logger.exception(f'Problem adding new sw asset {new_asset_data}')
                except Exception:
                    logger.exception(f'Problem adding software to {device_raw}')

                try:
                    if isinstance(device_raw['asset_software_data'], list):
                        for asset_data in device_raw['asset_software_data']:
                            try:
                                if asset_data.get('ProductName0'):

                                    if get_settings_cached()['should_populate_heavy_fields']:
                                        source_ais = 'SCCM INSTALLED_SOFTWARE Table'
                                    else:
                                        source_ais = None

                                    device.add_installed_software(
                                        name=asset_data.get('ProductName0'), version=asset_data.get('ProductVersion0'),
                                        source=source_ais
                                    )
                            except Exception:
                                logger.exception(f'Problem adding asset {asset_data}')
                except Exception:
                    logger.exception(f'Problem adding software to {device_raw}')

                try:
                    if isinstance(device_raw['asset_program_data'], list):
                        for asset_data in device_raw['asset_program_data']:
                            try:
                                if asset_data.get('DisplayName0'):

                                    if get_settings_cached()['should_populate_heavy_fields']:
                                        source_ais = 'SCCM ADD_REMOVE_PROGRAMS Table'
                                    else:
                                        source_ais = None

                                    device.add_installed_software(
                                        name=asset_data.get('DisplayName0'), version=asset_data.get('Version0'),
                                        source=source_ais
                                    )
                            except Exception:
                                logger.exception(f'Problem adding asset {asset_data}')
                except Exception:
                    logger.exception(f'Problem adding program to {device_raw}')

                try:
                    if isinstance(device_raw['patch_data'], list):
                        for patch_data in device_raw['patch_data']:
                            try:
                                patch_description = patch_data.get('Description0') or ''
                                if patch_data.get('FixComments0'):
                                    patch_description += ' Hotfix Comments:' + patch_data.get('FixComments0')
                                if not patch_description:
                                    patch_description = None
                                installed_on = parse_date(patch_data.get('InstallDate0'))
                                if not installed_on:
                                    installed_on = parse_date(patch_data.get('InstalledOn0'))
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
                    'name': 'drop_no_last_seen',
                    'title': 'Do not fetch devices without \'Last Seen\'',
                    'type': 'bool'
                },
                {
                    'name': 'devices_fetched_at_a_time',
                    'type': 'integer',
                    'title': 'SQL pagination'
                },
                {
                    'name': 'machine_domain_whitelist',
                    'title': 'Machine domain whitelist',
                    'type': 'string'
                }
            ],
            "required": ['drop_no_last_seen', 'exclude_ipv6', 'devices_fetched_at_a_time'],
            "pretty_name": "SCCM Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'exclude_ipv6': False,
            'drop_no_last_seen': False,
            'devices_fetched_at_a_time': 1000,
            'machine_domain_whitelist': None
        }

    def _on_config_update(self, config):
        self.__exclude_ipv6 = config['exclude_ipv6']
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
        self.__drop_no_last_seen = config.get('drop_no_last_seen') or False
        self.__machine_domain_whitelist = config.get('machine_domain_whitelist').lower().split(',') \
            if config.get('machine_domain_whitelist') else None
