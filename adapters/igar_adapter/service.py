import datetime
import ipaddress
import logging
import chardet
from axonius.adapter_exceptions import ClientConnectionException

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.users.user_adapter import UserAdapter
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import make_dict_from_csv
from igar_adapter.connection import IgarConnection

logger = logging.getLogger(f'axonius.{__name__}')


class ApplicationData(SmartJsonClass):
    application_name = Field(str, 'Application Name')
    application_id = Field(str, 'Application ID')
    is_manager = Field(str, 'IS Manager')
    owning_country_code = Field(str, 'Owning Country Code')
    owning_company_code = Field(str, 'Owning Company Code')
    owning_function = Field(str, 'Owning Function')
    application_support_status = Field(str, 'Application Support Status')
    internal_control_relevance = Field(str, 'Internal Control Relevance')
    abbsoxtesting = Field(str, 'ABBSOXTesting')
    eysoxtesting = Field(str, 'EYSOXTesting')
    installation_type = Field(str, 'Installation Type')
    internet_facing = Field(str, 'Internet Facing')
    webfacing = Field(str, 'WebFacing')
    level_used = Field(str, 'Level Used')
    owning_division_code = Field(str, 'Owning Division Code')
    application_owner = Field(str, 'Application Owner')
    application_url = Field(str, 'Application URL')
    description = Field(str, 'Application Description')


class IgarAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Device Type', description='Server or Network Equipment',
                            enum=['Server', 'Network Equipment'])
        comments = Field(str, 'Comments')
        # server stuff
        igar_server_id = Field(str, 'Igar Server ID')
        has_ip_duplication = Field(bool, 'Has IP Duplication')
        last_modified = Field(datetime.datetime, 'Last Modified')
        network_zone = Field(str, 'Network Zone')
        owner_email = Field(str, 'Owner Email')
        owner_geid = Field(str, 'Owner Geid')
        support_status = Field(str, 'Support Status')
        asset_support = Field(str, 'Asset Support')
        device_status = Field(str, 'Device Status')
        role = Field(str, 'Role')
        nstatus = Field(str, 'NStatus')
        decomissioned_date = Field(datetime.datetime, 'Decomissioned Date')
        server_class = Field(str, 'Server Class')
        service_level_classification = Field(str, 'Service Level Classification')
        owning_country_code = Field(str, 'Owning Country Code')
        owning_country = Field(str, 'Owning Country')
        owning_org = Field(str, 'Owning Organization')
        owning_division = Field(str, 'Owning Divison')
        location_country_code = Field(str, 'Location Country Code')
        location_id = Field(str, 'Location ID')
        applications_data = ListField(ApplicationData, 'Applications Data')
        server_country_code = Field(str, 'Server Country Code')
        type_of_vm_scan = Field(str, 'Type Of VM Scan')
        authentication_record = Field(str, 'Authentication Record')
        scan_group_field = Field(str, 'Scan Group Field')
        data_center_id = Field(str, 'Data Center ID')
        panned_availability_period = Field(str, 'Panned Availability Period')
        ci_number = Field(str, 'CI Number')
        server_environent_supported_by = Field(str, 'Server Environent Supported By')
        manua_host_ip_address = Field(str, 'Manual Host IP Address')
        # network equipment stuff
        att_active = Field(str, 'ATTActive')
        addr_geid = Field(str, 'Address GEID')
        addr_geid_from_ip = Field(str, 'Address GEID from IP')
        ownership_status = Field(str, 'Asset Ownership Status')
        is_deleted = Field(bool, 'Deleted')
        sub_type = Field(str, 'Device Sub-Type')
        network_device_type = Field(str, 'Network Equipment Type')
        equipment_id = Field(int, 'Equipment ID')
        is_included_hld_lld = Field(bool, 'Is Included HLD/LLD')
        initial_delivery_date = Field(datetime.datetime, 'Initial Delivery Date')
        is_confirmed = Field(bool, 'Is Confirmed')
        is_external = Field(bool, 'Is External')
        maintenance_exp_date = Field(datetime.datetime, 'Maintenance Expiry Date')
        new_device_type = Field(str, 'New Device Type')
        new_purchase_date = Field(datetime.datetime, 'New Purchased Date')
        new_purchase_status = Field(str, 'New Purchased Status')
        ref_number = Field(str, 'Reference Number')
        router_short_hostname = Field(str, 'Router Short Host Name')
        sw_version = Field(str, 'SW Version')
        site_code = Field(str, 'Site Code')
        switch_name_or_ip = Field(str, 'Switch Name or IP')
        is_transferred_to_snow = Field(bool, 'Is Transferred to SNOW')
        is_under_maintenance = Field(bool, 'Is Under Maintenance')
        used_for = Field(str, 'Used For')

    class MyUserAdapter(UserAdapter):
        applications_data = ListField(ApplicationData, 'Applications Data')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        if client_config.get('wsdl_url'):
            return client_config['wsdl_url']
        return client_config['igar_servers_file_name'] + '_' +\
            client_config['igar_servers_applications_file_name'] + \
            '_' + client_config['igar_applications_file_name']

    def _test_reachability(self, client_config):
        if client_config.get('wsdl_url'):
            return IgarConnection.test_reachability(client_config['wsdl_url'])
        return all([client_config.get('igar_servers_file_name'),
                    client_config.get('igar_servers_file'),
                    client_config.get('igar_servers_applications_file_name'),
                    client_config.get('igar_servers_applications_file'),
                    client_config.get('igar_applications_file_name'),
                    client_config.get('igar_applications_file')])

    def _create_csv_data_from_file(self, csv_file):
        csv_data_bytes = self._grab_file_contents(csv_file)

        encoding = chardet.detect(csv_data_bytes)['encoding']  # detect decoding automatically
        encoding = encoding or 'utf-8'
        csv_data = csv_data_bytes.decode(encoding)
        csv_dict = make_dict_from_csv(csv_data)
        return csv_dict

    @staticmethod
    def _get_connection(client_config):
        connection = IgarConnection(domain=client_config['wsdl_url'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            if client_config.get('wsdl_url'):
                return self._get_connection(client_config)
            self._get_csv_data(client_config)
            return client_config
        except Exception as e:
            message = f'Error obtaining iGAR information: Verify configuration {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_users_by_client(self, key, data):
        """
        Return tuple: servers_data, servers_apps_data, apps_data
        :param key: connection name
        :param data: connection (csv files info or IGARConnection)
        :return: tuple(servers_data, servers_apps_data, apps_data)
        """
        if isinstance(data, IgarConnection):
            with data:
                return data.get_users_list()
        return self._get_csv_data(data)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Return tuple: servers_data, servers_apps_data, apps_data, network_eq_data
        :param client_name: connection name
        :param client_data: connection (csv files info or IGARConnection)
        :return: tuple(servers_data, servers_apps_data, apps_data, network_eq_data)
        """
        if isinstance(client_data, IgarConnection):
            with client_data:
                return client_data.get_device_list()
        return (*self._get_csv_data(client_data), [])  # eq list is empty in case of csv

    def _get_csv_data(self, client_data):
        servers_data = self._create_csv_data_from_file(client_data['igar_servers_file'])
        servers_applications_data = self._create_csv_data_from_file(client_data['igar_servers_applications_file'])
        applications_data = self._create_csv_data_from_file(client_data['igar_applications_file'])
        return servers_data, servers_applications_data, applications_data

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {
                    'name': 'wsdl_url',
                    'title': 'iGAR Web API Service WSDL URL',
                    'type': 'string'
                },
                {
                    'name': 'igar_servers_file_name',
                    'title': 'iGAR Servers File Name',
                    'type': 'string'
                },
                {
                    'name': 'igar_servers_file',
                    'title': 'iGAR Servers File',
                    'description': 'The binary contents of the csv',
                    'type': 'file',
                },
                {
                    'name': 'igar_servers_applications_file_name',
                    'title': 'iGAR Applications To Servers File Name',
                    'type': 'string'
                },
                {
                    'name': 'igar_servers_applications_file',
                    'title': 'iGAR Applications To Servers File',
                    'description': 'The binary contents of the csv',
                    'type': 'file',
                },
                {
                    'name': 'igar_applications_file_name',
                    'title': 'iGAR Applications File Name',
                    'type': 'string'
                },
                {
                    'name': 'igar_applications_file',
                    'title': 'iGAR Applications File',
                    'description': 'The binary contents of the csv',
                    'type': 'file',
                },
            ],
            'required': [
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    # pylint: disable=arguments-differ, too-many-locals
    def _parse_users_raw_data(self, raw_data):
        servers_data, servers_applications_data, applications_data = raw_data
        users_data_dict = dict()

        for application_raw in applications_data:
            try:
                # modified for compatibility with web service data
                application_owner = application_raw.get('Application_Owner') or application_raw.get('ApplicationOwner')
                if not application_owner:
                    continue
                application_id = application_raw.get('InstallationID')
                if isinstance(application_id, dict):
                    application_id = application_id.get('string')
                application_data = ApplicationData(
                    application_name=application_raw.get('Application_Name'),
                    application_id=application_id,
                    is_manager=application_raw.get('IS_Manager'),
                    owning_country_code=application_raw.get('Owning_Country_Code'),
                    owning_company_code=application_raw.get('Owning_Company_Code'),
                    owning_function=application_raw.get('Owning_function') or application_raw.get('OwningFunction'),
                    application_support_status=application_raw.get(
                        'ApplicationSupportStatus') or str(application_raw.get('support')),
                    internal_control_relevance=application_raw.get('Internal_Control_Relevance'),
                    abbsoxtesting=application_raw.get('ABBSOXTesting'),
                    eysoxtesting=application_raw.get('EYSOXTesting'),
                    installation_type=application_raw.get(
                        'InstallationType') or application_raw.get('Installation_Type'),
                    internet_facing=str(application_raw.get('InternetFacing')),
                    webfacing=application_raw.get('webfacing'),
                    level_used=application_raw.get('Level_Used'),
                    owning_division_code=application_raw.get('Owning_Division_Code'),
                    application_owner=application_owner,
                    application_url=application_raw.get('ApplicationUrl'),
                    description=application_raw.get('Application_description'))
                application_owner = application_owner.lower()
                if application_owner not in users_data_dict:
                    users_data_dict[application_owner] = []
                users_data_dict[application_owner].append(('app', application_data))
            except Exception:
                logger.exception(f'Problem with application raw {application_raw}')
        for device_raw in servers_data:
            try:
                server_owner = device_raw.get('Owner Email') or device_raw.get('OwnerEmail')
                if not server_owner:
                    continue
                server_owner = server_owner.lower()
                if server_owner not in users_data_dict:
                    users_data_dict[server_owner] = []
                name = device_raw.get('ServerName')
                system_owner = device_raw.get('System Owner') or device_raw.get('SystemOwner')
                support_status = device_raw.get('Support Status') or device_raw.get('SupportStatus')
                users_data_dict[server_owner].append(('server', [name, system_owner, support_status]))
            except Exception:
                logger.exception(f'Problem getting users stuff for: {str(device_raw)}')
        for user_mail, user_data in users_data_dict.items():
            try:
                user = self._new_user_adapter()
                user.id = user_mail
                user.mail = user_mail
                for user_data_raw_full in user_data:
                    data_type, user_data_raw = user_data_raw_full
                    if data_type == 'app':
                        user.applications_data.append(user_data_raw)
                    elif data_type == 'server':
                        name, system_owner, server_status = user_data_raw
                        if system_owner:
                            user.username = system_owner
                        if name:
                            user.add_associated_device(device_caption=name,
                                                       device_status=server_status)
                yield user
            except Exception:
                logger.exception(f'Problem with user mail {user_mail}')

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, (bool, int)):
            return bool(value)
        return None

    # pylint: disable=too-many-locals
    def _parse_raw_data(self, devices_raw_data):
        servers_data, servers_applications_data, applications_data, equipment_data = devices_raw_data

        yield from self._create_servers_devices(applications_data, servers_applications_data, servers_data)
        yield from self._create_net_equipment_devices(equipment_data)

    def _create_net_equipment_devices(self, equipment_data):
        for device_raw in equipment_data:
            try:
                if not isinstance(device_raw, dict):
                    continue
                device = self._new_device_adapter()
                eq_id = str(device_raw.get('EquipmentId') or '')
                if not eq_id:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = eq_id + '_' + (device_raw.get('DeviceName') or '')
                device.name = device_raw.get('DeviceName')
                device.device_manufacturer = device_raw.get('Manufacturer')
                device.device_serial = device_raw.get('SerialNumber')
                device.device_model = device_raw.get('DeviceModel')
                device.owner = device_raw.get('AssetOwnedBy')
                device.device_managed_by = device_raw.get('ManagedBy')
                device.physical_location = device_raw.get('Location')
                try:
                    ips = list()
                    ip_addr = device_raw.get('IPAddress')
                    switch_name_or_ip = device_raw.get('SwitchNameOrIP')
                    if ip_addr:
                        ips.append(ip_addr)
                    if switch_name_or_ip:
                        try:
                            ip_switch = str(ipaddress.ip_address(switch_name_or_ip))
                            if ip_switch != ip_addr:
                                ips.append(ip_switch)
                        except Exception:
                            logger.debug(f'switch_name_or_ip {switch_name_or_ip} is not a valid ip.')
                    if ips:
                        device.add_nic(ips=ips)
                except Exception as e:
                    logger.warning(f'Failed to add IP to device {device_raw}: {str(e)}')

                # And now for specific fields
                device.comments = device_raw.get('Comments')
                device.att_active = device_raw.get('ATTActive')
                device.addr_geid = device_raw.get('AddressGEID')
                device.addr_geid_from_ip = device_raw.get('AddressGEIDFromIP')
                device.ownership_status = device_raw.get('AssetOwnershipStatus')
                device.is_deleted = self._parse_bool(device_raw.get('Deleted'))
                device.sub_type = device_raw.get('DeviceSubType')
                device.network_device_type = device_raw.get('DeviceType')
                device.equipment_id = device_raw.get('EquipmentId')
                device.is_included_hld_lld = self._parse_bool(device_raw.get('IncludedHLDLLD'))
                device.initial_delivery_date = parse_date(device_raw.get('InitialDeliveryDate'))
                device.is_confirmed = self._parse_bool(device_raw.get('IsConfirmed'))
                device.is_external = self._parse_bool(device_raw.get('IsExternal'))
                device.maintenance_exp_date = parse_date(device_raw.get('MaintenanceExpiryDate'))
                device.new_device_type = device_raw.get('NewDeviceType')
                device.new_purchase_date = parse_date(device_raw.get('NewPurchasedDate'))
                device.new_purchase_status = device_raw.get('NewPurchasedStatus')
                device.ref_number = device_raw.get('ReferenceNumber')
                short_host_name = device_raw.get('RouterShortHostName')
                if short_host_name:
                    device.hostname = short_host_name
                device.router_short_hostname = short_host_name
                device.sw_version = device_raw.get('SWVersion')
                device.site_code = device_raw.get('SiteCode')
                device.switch_name_or_ip = device_raw.get('SwitchNameOrIP')
                device.is_transferred_to_snow = self._parse_bool(device_raw.get('TransferredToSNOW'))
                device.is_under_maintenance = self._parse_bool(device_raw.get('UnderMaintenance'))
                device.used_for = device_raw.get('UsedFor')

                device.device_type = 'Network Equipment'
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem adding device: {str(device_raw)}')

    def _create_servers_devices(self, applications_data, servers_applications_data, servers_data):
        application_data_dict = dict()
        server_applications_dict = dict()
        for application_raw in applications_data:
            try:
                application_id = application_raw.get('InstallationID')
                if isinstance(application_id, dict):
                    application_id = application_id['string']
                if not application_id:
                    continue
                application_data = ApplicationData(
                    application_name=application_raw.get('Application_Name'),
                    application_id=application_id,
                    is_manager=application_raw.get('IS_Manager'),
                    owning_country_code=application_raw.get('Owning_Country_Code'),
                    owning_company_code=application_raw.get('Owning_Company_Code'),
                    owning_function=application_raw.get('Owning_function') or application_raw.get('OwningFunction'),
                    application_support_status=application_raw.get(
                        'ApplicationSupportStatus') or str(application_raw.get('support')),
                    internal_control_relevance=application_raw.get('Internal_Control_Relevance'),
                    abbsoxtesting=application_raw.get('ABBSOXTesting'),
                    eysoxtesting=application_raw.get('EYSOXTesting'),
                    installation_type=application_raw.get(
                        'InstallationType') or application_raw.get('Installation_Type'),
                    internet_facing=str(application_raw.get('InternetFacing')),
                    webfacing=application_raw.get('webfacing'),
                    level_used=application_raw.get('Level_Used'),
                    owning_division_code=application_raw.get('Owning_Division_Code'),
                    application_owner=application_raw.get(
                        'Application_Owner') or application_raw.get('ApplicationOwner'),
                    application_url=application_raw.get('ApplicationUrl'),
                    description=application_raw.get('Application_description'))
                application_data_dict[application_id] = application_data
            except Exception:
                logger.exception(f'Problem with application raw {application_raw}')
        for server_application_raw in servers_applications_data:
            try:
                server_id = server_application_raw.get('ServerID') or server_application_raw.get('ServerId')
                application_id = server_application_raw.get('ApplicationID') or \
                    server_application_raw.get('InstallationId')
                if isinstance(application_id, dict):
                    application_id = application_id['string']
                if not (server_id and application_id):
                    continue
                if server_id not in server_applications_dict:
                    server_applications_dict[server_id] = []
                if isinstance(application_id, list):
                    server_applications_dict[server_id].extend(application_id)  # For web client
                else:
                    server_applications_dict[server_id].append(application_id)  # For CSV
            except Exception:
                logger.exception(f'Problem with server application {server_application_raw}')
        servers_data = list(servers_data)
        ips_dups = list(self._get_ips_dups(servers_data))
        logger.debug(f'Ips Dups are {ips_dups}')
        for device_raw in servers_data:
            try:
                device = self._new_device_adapter()
                server_id = device_raw.get('ServerId')
                if not server_id:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = str(server_id) + '_' + (device_raw.get('ServerName') or '')
                device.igar_server_id = str(server_id)
                device.has_ip_duplication = False
                device.name = device_raw.get('ServerName')
                device.hostname = device_raw.get('ServerFQDN')
                server_ip_raw = device_raw.get('ServerIP') or device_raw.get('IP')
                ips = list()
                if isinstance(server_ip_raw, str) and server_ip_raw:
                    if ',' in server_ip_raw:
                        server_ips = server_ip_raw.split(',')
                    else:
                        server_ips = [server_ip_raw.strip()]
                else:
                    server_ips = []
                for server_ip in server_ips:
                    server_ip = server_ip.strip()
                    if not server_ip:
                        continue
                    if server_ip in ips_dups:
                        device.has_ip_duplication = True
                    ips.extend([ip.strip() for ip in server_ip.split('^')])
                if ips:
                    device.add_nic(ips=ips)
                manual_host_ip = device_raw.get('ManualHostIPAddress') or device_raw.get('ManualHostIpAddress')
                if isinstance(manual_host_ip, str) and manual_host_ip:
                    if ',' in manual_host_ip:
                        ips = [ip.strip() for ip in manual_host_ip.split(',')]
                    else:
                        ips = [ip.strip() for ip in manual_host_ip.split('^')]
                    device.add_nic(ips=ips)
                device.manua_host_ip_address = manual_host_ip
                apps_ids = server_applications_dict.get(server_id)
                if not apps_ids:
                    apps_ids = []
                for app_id in apps_ids:
                    try:
                        if application_data_dict.get(app_id):
                            device.applications_data.append(application_data_dict.get(app_id))
                    except Exception:
                        logger.exception(f'Problem with app id {app_id}')
                device.network_zone = device_raw.get('Network Zone') or device_raw.get('NetworkZone')
                device.owner = device_raw.get('System Owner') or device_raw.get('AssetOwnedBy')
                device.owner_email = device_raw.get('Owner Email') or device_raw.get('OwnerEmail')
                device.owner_geid = device_raw.get('Owner GEID') or str(device_raw.get('OwnerGEID'))
                device.support_status = device_raw.get('Support Status') or device_raw.get('SupportStatus')
                device.asset_support = device_raw.get('Asset Support') or device_raw.get('AssetSupportStatus')
                device.device_status = device_raw.get('Status')
                device.role = device_raw.get('Role')
                device.nstatus = device_raw.get('NStatus') or device_raw.get('nStatus')
                device.decomissioned_date = parse_date(device_raw.get('Decomissioned Date') or
                                                       device_raw.get('DecomissionDate'))
                device.server_class = device_raw.get('Server Class') or device_raw.get('ServerClass')
                device.service_level_classification = device_raw.get('Service Level Classification') or \
                    device_raw.get('ServiceLevelClassification')
                device.figure_os(device_raw.get('OS'))
                device.owning_country_code = device_raw.get('Owning Country Code') or \
                    device_raw.get('OwningCountryCode')
                device.owning_country = device_raw.get('Owning Country') or device_raw.get('OwningCountry')
                device.owning_org = device_raw.get('Owning ORG') or device_raw.get('OwningOrg')
                device.owning_division = device_raw.get('OwningDivision')
                device.location_country_code = device_raw.get('LocationCountryCode')
                device.location_id = device_raw.get('LocationID')
                device.server_country_code = device_raw.get('ServerCountryCode')
                device.last_modified = parse_date(device_raw.get('Last Modified Date') or
                                                  device_raw.get('LastModifiedDate'))
                device.type_of_vm_scan = device_raw.get('TypeOfVMScan')
                device.authentication_record = device_raw.get('AuthenticationRecord')
                device.scan_group_field = device_raw.get('ScanGroupField')
                device.data_center_id = device_raw.get('DataCenterID') or str(device_raw.get('DataCenterId'))
                device.comments = device_raw.get('Comments')
                device.panned_availability_period = device_raw.get('PannedAvailabilityPeriod')
                device.ci_number = device_raw.get('CINumber')
                device.server_environent_supported_by = device_raw.get('Server_Environent_Supported_By') or \
                    device_raw.get('ServerEnvironentSupportedBy')
                device.device_type = 'Server'
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem adding device: {str(device_raw)}')

    @staticmethod
    def _get_ips_dups(servers_data):
        ips_seen = set()
        ips_dups = set()
        for device_raw in servers_data:
            try:
                ip_raw = device_raw.get('ServerIP') or device_raw.get('IP')
                if not (isinstance(ip_raw, str) and ip_raw):
                    continue
                if ',' in ip_raw:
                    ip_list = ip_raw.split(',')
                else:
                    ip_list = [ip_raw]
                for ip in ip_list:
                    ip = ip.strip()
                    if not ip:
                        continue
                    if ip in ips_seen:
                        ips_dups.add(ip)
                    ips_seen.add(ip)
            except Exception:
                logger.exception(f'Problem getting ips stuff for: {str(device_raw)}')
        return ips_dups

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
