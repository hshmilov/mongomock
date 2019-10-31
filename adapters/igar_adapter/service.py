import datetime
import logging
import chardet

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.users.user_adapter import UserAdapter
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import make_dict_from_csv

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
    application_owner = Field(str, 'Appilcation Owner')


class IgarAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        has_ip_duplication = Field(bool, 'Has IP Duplication')
        last_modified = Field(datetime.datetime, 'Last Modified')
        network_zone = Field(str, 'Network Zone')
        system_owner = Field(str, 'System Owner')
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
        comments = Field(str, 'Comments')
        panned_availability_period = Field(str, 'Panned Availability Period')
        ci_number = Field(str, 'CI Number')
        server_environent_supported_by = Field(str, 'Server Environent Supported By')
        manua_host_ip_address = Field(str, 'Manual Host IP Address')

    class MyUserAdapter(UserAdapter):
        applications_data = ListField(ApplicationData, 'Applications Data')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['igar_servers_file_name'] + '_' +\
            client_config['igar_servers_applications_file_name'] + \
            '_' + client_config['igar_applications_file_name']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _query_users_by_client(self, key, data):
        servers_data = self._create_csv_data_from_file(data['igar_servers_file'])
        servers_applications_data = self._create_csv_data_from_file(data['igar_servers_applications_file'])
        applications_data = self._create_csv_data_from_file(data['igar_applications_file'])
        return servers_data, servers_applications_data, applications_data

    def _create_csv_data_from_file(self, csv_file):
        csv_data_bytes = self._grab_file_contents(csv_file)

        encoding = chardet.detect(csv_data_bytes)['encoding']  # detect decoding automatically
        encoding = encoding or 'utf-8'
        csv_data = csv_data_bytes.decode(encoding)
        csv_dict = make_dict_from_csv(csv_data)
        return csv_dict

    def _connect_client(self, client_config):
        self._create_csv_data_from_file(client_config['igar_servers_file'])
        self._create_csv_data_from_file(client_config['igar_servers_applications_file'])
        self._create_csv_data_from_file(client_config['igar_applications_file'])
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        servers_data = self._create_csv_data_from_file(client_data['igar_servers_file'])
        servers_applications_data = self._create_csv_data_from_file(client_data['igar_servers_applications_file'])
        applications_data = self._create_csv_data_from_file(client_data['igar_applications_file'])
        return servers_data, servers_applications_data, applications_data

    @staticmethod
    def _clients_schema():
        return {
            'items': [
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
                'igar_servers_file_name',
                'igar_servers_file',
                'igar_servers_applications_file_name',
                'igar_servers_applications_file',
                'igar_applications_file_name',
                'igar_applications_file'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, raw_data):
        servers_data, servers_applications_data, applications_data = raw_data
        users_data_dict = dict()

        for application_raw in applications_data:
            try:
                application_owner = application_raw.get('Application_Owner')
                if not application_owner:
                    continue
                application_owner = application_owner.lower()
                application_data = ApplicationData(application_name=application_raw.get('Application_Name'),
                                                   application_id=application_raw.get('InstallationID'),
                                                   is_manager=application_raw.get('IS_Manager'),
                                                   owning_country_code=application_raw.get('Owning_Country_Code'),
                                                   owning_company_code=application_raw.get('Owning_Company_Code'),
                                                   owning_function=application_raw.get('Owning_function'),
                                                   application_support_status=application_raw.get(
                                                       'ApplicationSupportStatus'),
                                                   internal_control_relevance=application_raw.get(
                                                       'Internal_Control_Relevance'),
                                                   abbsoxtesting=application_raw.get('ABBSOXTesting'),
                                                   eysoxtesting=application_raw.get('EYSOXTesting'),
                                                   installation_type=application_raw.get('InstallationType'),
                                                   internet_facing=application_raw.get('InternetFacing'),
                                                   webfacing=application_raw.get('webfacing'),
                                                   level_used=application_raw.get('Level_Used'),
                                                   owning_division_code=application_raw.get('Owning_Division_Code'),
                                                   application_owner=application_raw.get('Application_Owner'))
                if application_owner not in users_data_dict:
                    users_data_dict[application_owner] = []
                users_data_dict[application_owner].append(('app', application_data))
            except Exception:
                logger.exception(f'Problem with application raw {application_raw}')
        for device_raw in servers_data:
            try:
                if not device_raw.get('Owner Email'):
                    continue
                server_owner = device_raw.get('Owner Email').lower()
                if server_owner not in users_data_dict:
                    users_data_dict[server_owner] = []
                name = device_raw.get('ServerName')
                system_owner = device_raw.get('System Owner')
                users_data_dict[server_owner].append(('server', [name, system_owner,
                                                                 device_raw.get('Support Status')]))
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

    def _parse_raw_data(self, devices_raw_data):
        servers_data, servers_applications_data, applications_data = devices_raw_data

        application_data_dict = dict()
        server_applications_dict = dict()

        for application_raw in applications_data:
            try:
                application_id = application_raw.get('InstallationID')
                if not application_id:
                    continue
                application_data = ApplicationData(application_name=application_raw.get('Application_Name'),
                                                   application_id=application_raw.get('InstallationID'),
                                                   is_manager=application_raw.get('IS_Manager'),
                                                   owning_country_code=application_raw.get('Owning_Country_Code'),
                                                   owning_company_code=application_raw.get('Owning_Company_Code'),
                                                   owning_function=application_raw.get('Owning_function'),
                                                   application_support_status=application_raw.get(
                                                       'ApplicationSupportStatus'),
                                                   internal_control_relevance=application_raw.get(
                                                       'Internal_Control_Relevance'),
                                                   abbsoxtesting=application_raw.get('ABBSOXTesting'),
                                                   eysoxtesting=application_raw.get('EYSOXTesting'),
                                                   installation_type=application_raw.get('InstallationType'),
                                                   internet_facing=application_raw.get('InternetFacing'),
                                                   webfacing=application_raw.get('webfacing'),
                                                   level_used=application_raw.get('Level_Used'),
                                                   owning_division_code=application_raw.get('Owning_Division_Code'),
                                                   application_owner=application_raw.get('Application_Owner'))
                application_data_dict[application_id] = application_data
            except Exception:
                logger.exception(f'Problem with application raw {application_raw}')
        for server_application_raw in servers_applications_data:
            try:
                server_id = server_application_raw.get('ServerID')
                application_id = server_application_raw.get('ApplicationID')
                if not server_id or not application_id:
                    continue
                if server_id not in server_applications_dict:
                    server_applications_dict[server_id] = []
                server_applications_dict[server_id].append(application_id)
            except Exception:
                logger.exception(f'Problem with server application {server_application_raw}')
        servers_data = list(servers_data)
        ips_seen = set()
        ips_dups = set()
        for device_raw in servers_data:
            try:
                if device_raw.get('ServerIP'):
                    if device_raw.get('ServerIP') in ips_seen:
                        ips_dups.add(device_raw.get('ServerIP'))
                    ips_seen.add(device_raw.get('ServerIP'))
            except Exception:
                logger.exception(f'Problem getting ips stuff for: {str(device_raw)}')
        ips_dups = list(ips_dups)
        logger.debug(f'Ips Dups are {ips_dups}')
        for device_raw in servers_data:
            try:
                device = self._new_device_adapter()
                server_id = device_raw.get('ServerId')
                if not server_id:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = server_id + '_' + (device_raw.get('ServerName') or '')
                device.has_ip_duplication = False
                device.name = device_raw.get('ServerName')
                device.hostname = device_raw.get('ServerFQDN')
                if device_raw.get('ServerIP'):
                    if device_raw.get('ServerIP') in ips_dups:
                        device.has_ip_duplication = True
                    ips = [ip.strip() for ip in device_raw.get('ServerIP').split('^')]
                    device.add_nic(ips=ips)
                if device_raw.get('ManualHostIPAddress'):
                    ips = [ip.strip() for ip in device_raw.get('ManualHostIPAddress').split('^')]
                    device.add_nic(ips=ips)
                device.manua_host_ip_address = device_raw.get('ManualHostIPAddress')
                apps_ids = server_applications_dict.get(server_id)
                if not apps_ids:
                    apps_ids = []
                for app_id in apps_ids:
                    try:
                        if application_data_dict.get(app_id):
                            device.applications_data.append(application_data_dict.get(app_id))
                    except Exception:
                        logger.exception(f'Problem with app id {app_id}')
                device.network_zone = device_raw.get('Network Zone')
                device.system_owner = device_raw.get('System Owner')
                device.owner_email = device_raw.get('Owner Email')
                device.owner_geid = device_raw.get('Owner GEID')
                device.support_status = device_raw.get('Support Status')
                device.asset_support = device_raw.get('Asset Support')
                device.device_status = device_raw.get('Status')
                device.role = device_raw.get('Role')
                device.nstatus = device_raw.get('NStatus')
                device.decomissioned_date = parse_date(device_raw.get('Decomissioned Date'))
                device.server_class = device_raw.get('Server Class')
                device.service_level_classification = device_raw.get('Service Level Classification')
                device.figure_os(device_raw.get('OS'))
                device.owning_country_code = device_raw.get('Owning Country Code')
                device.owning_country = device_raw.get('Owning Country')
                device.owning_org = device_raw.get('Owning ORG')
                device.owning_division = device_raw.get('OwningDivision')
                device.location_country_code = device_raw.get('LocationCountryCode')
                device.location_id = device_raw.get('LocationID')
                device.server_country_code = device_raw.get('ServerCountryCode')
                device.last_modified = parse_date(device_raw.get('Last Modified Date'))
                device.type_of_vm_scan = device_raw.get('TypeOfVMScan')
                device.authentication_record = device_raw.get('AuthenticationRecord')
                device.scan_group_field = device_raw.get('ScanGroupField')
                device.data_center_id = device_raw.get('DataCenterID')
                device.comments = device_raw.get('Comments')
                device.panned_availability_period = device_raw.get('PannedAvailabilityPeriod')
                device.ci_number = device_raw.get('CINumber')
                device.server_environent_supported_by = device_raw.get('Server_Environent_Supported_By')
                yield device
            except Exception:
                logger.exception(f'Problem adding device: {str(device_raw)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
