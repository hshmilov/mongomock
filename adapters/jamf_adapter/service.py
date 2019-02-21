import logging


from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, JsonStringFormat, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import format_ip
from axonius.mixins.configurable import Configurable
from jamf_adapter import consts
from jamf_adapter.connection import JamfConnection, JamfPolicy
from jamf_adapter.exceptions import JamfException

logger = logging.getLogger(f'axonius.{__name__}')


class JamfLocation(SmartJsonClass):
    building = Field(str, 'Building')
    department = Field(str, 'Department')
    email_address = Field(str, 'Email Address')
    phone_number = Field(str, 'Phone Number')
    real_name = Field(str, 'Real Name')
    room = Field(str, 'Room')
    username = Field(str, 'Username')


class JamfSite(SmartJsonClass):
    """ A definition for a Jamf site field"""
    id = Field(int, "Site Id")
    name = Field(str, "Site Name")


class JamfProfile(SmartJsonClass):
    """ A definition for a Jamf profile"""
    version = Field(str, "Profile Version")
    display_name = Field(str, "Profile Display Name")
    identifier = Field(str, "Profile Identifier")
    uuid = Field(str, "Profile UUID")


class JamfAdapter(AdapterBase, Configurable):

    class MyDeviceAdapter(DeviceAdapter):
        public_ip = Field(str, 'Public IP', converter=format_ip, json_format=JsonStringFormat.ip)
        jamf_location = Field(JamfLocation, 'Jamf Location')
        policies = ListField(JamfPolicy, "Jamf Policies")
        is_managed = Field(bool, 'Is Managed')
        profiles = ListField(JamfProfile, "Jamf Profiles")
        jamf_version = Field(str, 'Jamf Version')
        site = Field(JamfSite, "Jamf Sites")
        phone_number = Field(str, 'Phone Number')
        imei = Field(str, 'IMEI')
        disable_automatic_login = Field(str, 'Disable Automatic Login')
        alternative_mac = Field(str, 'Alternative MAC Address')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['Jamf_Domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get(consts.JAMF_DOMAIN))

    def _connect_client(self, client_config):
        try:
            connection = JamfConnection(domain=client_config[consts.JAMF_DOMAIN],
                                        users_db=self.users_db,
                                        http_proxy=client_config.get(consts.HTTP_PROXY),
                                        https_proxy=client_config.get(consts.HTTPS_PROXY)
                                        )
            connection.set_credentials(username=client_config[consts.USERNAME],
                                       password=client_config[consts.PASSWORD])
            connection.connect()
            return connection
        except JamfException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Jamf_Domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Jamf domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Jamf connection

        :return: A json with all the attributes returned from the Jamf Server
        """
        return client_data.get_devices(self.__fetch_department,
                                       self.__should_fetch_policies,
                                       self.__num_of_simultaneous_devices,
                                       self.__should_not_keepalive,
                                       self.__threads_time_sleep
                                       )

    def _clients_schema(self):
        """
        The schema JamfAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": consts.JAMF_DOMAIN,
                    "title": "Jamf Domain",
                    "type": "string"
                },
                {
                    "name": consts.USERNAME,
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": consts.PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": consts.HTTP_PROXY,
                    "title": "Http Proxy",
                    "type": "string"
                },
                {
                    "name": consts.HTTPS_PROXY,
                    "title": "Https Proxy",
                    "type": "string"
                }
            ],
            "required": [
                consts.JAMF_DOMAIN,
                consts.USERNAME,
                consts.PASSWORD
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                general_info = device_raw['general']

                udid = general_info.get('udid')
                if not udid:
                    logger.error(f"Error! got a device with no id: {device_raw}")
                    continue
                device.id = udid + '_' + (general_info.get('name') or '')

                device.name = general_info.get('name')
                try:
                    jamf_location_raw = device_raw.get('location')
                    if isinstance(jamf_location_raw, dict):
                        device.jamf_location = JamfLocation(
                            building=jamf_location_raw.get('building') if jamf_location_raw.get('building') else None,
                            department=jamf_location_raw.get(
                                'department') if jamf_location_raw.get('department') else None,
                            email_address=jamf_location_raw.get(
                                'email_address') if jamf_location_raw.get('email_address') else None,
                            phone_number=jamf_location_raw.get(
                                'phone_number') if jamf_location_raw.get('phone_number') else None,
                            real_name=jamf_location_raw.get(
                                'real_name') if jamf_location_raw.get('real_name') else None,
                            room=jamf_location_raw.get('room') if jamf_location_raw.get('room') else None,
                            username=jamf_location_raw.get('username') if jamf_location_raw.get('username') else None)
                except Exception:
                    logger.exception(f'Problem getting Jamf Location for {device_raw}')
                hostname = None
                # Ofri: Sometimes name is also the hostname. I saw that if we have one of these fields it can't be the host name.
                if not any(elem in device.name for elem in [' ', '.']):
                    asset_is_host = True
                    hostname = device.name
                    device.hostname = hostname
                else:
                    asset_is_host = False
                    host_no_spaces_list = device.name.replace(' ', '-').split('-')
                    host_no_spaces_list[0] = ''.join(char for char in host_no_spaces_list[0] if char.isalnum())
                    if len(host_no_spaces_list) > 1:
                        host_no_spaces_list[1] = ''.join(char for char in host_no_spaces_list[1] if char.isalnum())
                    hostname = '-'.join(host_no_spaces_list).split(".")[0]
                    device.hostname = hostname
                device.public_ip = general_info.get('ip_address')
                try:
                    site = general_info.get('site')
                    if site:
                        site_id = site.get('id')
                        if type(site_id) is not None:
                            site_id = int(site_id)
                        device.site = JamfSite(id=site_id, name=site.get('name'))
                except Exception:
                    logger.exception(f'device site is unexpected {device_raw}')

                device.device_serial = general_info.get("serial_number")
                if 'platform' in general_info:
                    # The field 'platform' means that we are handling a computer, and not a mobile.
                    # Thus we believe the following fields will be present.
                    last_contact_time_utc = general_info.get('last_contact_time_utc')
                    report_date = general_info.get('report_date')
                    try:
                        if last_contact_time_utc:
                            device.last_seen = parse_date(last_contact_time_utc)
                        elif report_date:
                            device.last_seen = parse_date(report_date)
                    except Exception:
                        logger.exception(f"Problem parsing last seen date {last_contact_time_utc} and {report_date}")
                    try:
                        is_managed = (general_info.get('remote_management') or {}).get('managed')
                        if is_managed is not None:
                            device.is_managed = is_managed == 'true'
                    except Exception:
                        logger.exception(f'Problem getting is managed for {general_info}')

                    device.jamf_version = general_info.get('jamf_version')
                    try:
                        ips = general_info.get('last_reported_ip').split(',') \
                            if general_info.get('last_reported_ip') else None
                        mac = general_info.get('mac_address') if general_info.get('mac_address') else None
                        if mac or ips:
                            device.add_nic(general_info.get('mac_address'), ips)
                        device.alternative_mac = general_info.get('alt_mac_address')
                    except Exception:
                        logger.exception(f"Problem adding nic to Jamf {str(device_raw)}")

                    hardware = device_raw.get('hardware', {})
                    device.figure_os(' '.join([hardware.get('os_name', ''),
                                               hardware.get('os_version', ''),
                                               hardware.get('processor_architecture', '')]))
                    device.os.build = hardware.get('os_build', '')

                    device.device_model = hardware.get('model_identifier')
                    device.device_model_family = hardware.get('model')

                    try:
                        groups_accounts = (device_raw.get('groups_accounts') or {})
                        users_raw = groups_accounts.get('local_accounts', [])
                        # This can come in a few formats
                        if users_raw is not None and isinstance(users_raw, dict) and users_raw.get("user"):
                            users_raw_user_object = users_raw["user"]
                            if isinstance(users_raw_user_object, dict):
                                users_raw = [users_raw_user_object]
                            elif isinstance(users_raw_user_object, list):
                                users_raw = users_raw_user_object
                            else:
                                users_raw = []
                        inventory_users_dict = dict()
                        try:
                            device.disable_automatic_login = (groups_accounts.get('user_inventories')
                                                              or {}).get('disable_automatic_login')
                            user_inventory_list = (groups_accounts.get('user_inventories')
                                                   or {}).get('user') or []
                            if not isinstance(user_inventory_list, list):
                                user_inventory_list = [user_inventory_list]
                            for user_inventory in user_inventory_list:
                                inventory_users_dict[user_inventory.get('username') or 'UNKNOWN'] = user_inventory
                        except Exception:
                            logger.exception(f'Problem getting inventory list')
                        device.last_used_users = []
                        for user_raw in users_raw:
                            try:
                                user_name_raw = user_raw.get('name')
                                user_inverntory_raw = inventory_users_dict.get(user_name_raw) or {}
                                if user_name_raw:
                                    device.last_used_users.append(user_name_raw)
                                device.add_users(username=user_raw.get('realname') + "@" + str(hostname),
                                                 user_sid=user_raw.get('uid'),
                                                 is_local=True,
                                                 is_admin=str(user_raw.get('administrator')).lower() == "true",
                                                 origin_unique_adapter_name=self.plugin_unique_name,
                                                 origin_unique_adapter_data_id=device.id,
                                                 user_department=user_raw.get("user_department"),
                                                 password_max_age=(int(user_inverntory_raw.get('password_max_age'))
                                                                   if user_inverntory_raw.get('password_max_age')
                                                                   else None)
                                                 )
                            except Exception:
                                logger.exception(f'Problem getting user {str(user_raw)}')
                    except Exception:
                        logger.exception(f'Problem getting users at {device_raw}')

                    total_ram_mb = hardware.get('total_ram_mb')
                    if total_ram_mb is not None:
                        try:
                            total_ram_mb = float(total_ram_mb)
                            device.total_physical_memory = total_ram_mb / 1024.0
                        except Exception:
                            logger.exception(f"Problem parsing total ram mb: {total_ram_mb}")

                    total_number_of_physical_procesors = hardware.get("number_processors")
                    if total_number_of_physical_procesors is not None:
                        try:
                            device.total_number_of_physical_processors = int(total_number_of_physical_procesors)
                        except Exception:
                            logger.exception(f"Problem parsing total namber of physical "
                                             f"processors: {total_number_of_physical_procesors}")

                    total_number_of_cores = hardware.get("number_cores")
                    if total_number_of_cores is not None:
                        try:
                            device.total_number_of_cores = int(total_number_of_cores)
                        except Exception:
                            logger.exception(f"Problem adding total number of cores {total_number_of_cores}")
                    processor_speed_mhz = hardware.get("processor_speed_mhz")
                    processor_type = hardware.get("processor_type")
                    if processor_speed_mhz is not None and processor_type is not None:
                        try:
                            device.add_cpu(
                                name=processor_type,
                                ghz=float(processor_speed_mhz) / 1024.0
                            )
                        except Exception:
                            logger.exception(f"Problem adding cpu {cpu}")
                    device.device_manufacturer = hardware.get('make')
                    try:
                        if self.__should_fetch_policies:
                            device.policies = device_raw['policies']

                            # Now transform this to dict so that we will put it as raw
                            device_raw['policies'] = [x.to_dict() for x in device_raw['policies']]
                    except Exception:
                        logger.exception(f"Problem adding policies of device raw")

                    drives = ((hardware.get('storage') or {}).get('device') or [])
                    drives = [drives] if type(drives) != list else drives
                    for drive in drives:
                        try:
                            partitions = drive.get('partition')
                            if not partitions:
                                continue
                            if not isinstance(partitions, list):
                                partitions = [partitions]
                            for partition in partitions:
                                if not partition:
                                    continue
                                total_size = partition.get('partition_capacity_mb')
                                if total_size:
                                    total_size = int(total_size) / 1024.0
                                free_size = partition.get('boot_drive_available_mb')
                                if free_size:
                                    free_size = int(free_size) / 1024.0
                                if any([free_size, total_size]):
                                    device.add_hd(total_size=total_size, free_size=free_size)
                        except Exception:
                            logger.exception(f"couldn't parse drive: {drive}")
                    active_directory_status = hardware.get('active_directory_status') or 'Not Bound'
                    if active_directory_status == 'Not Bound':
                        device.part_of_domain = False
                    else:
                        device.part_of_domain = True
                        if active_directory_status.lower().startswith('centrify: '):
                            active_directory_status = active_directory_status[len('centrify: '):]
                        device.domain = active_directory_status

                    applications = ((device_raw.get('software') or {}).get('applications') or {}).get('application', [])
                else:
                    try:
                        last_inventory_update_utc = parse_date(general_info.get('last_inventory_update_utc'))
                    except Exception:
                        logger.exception(f"Problem handling last inventory update utc")
                        last_inventory_update_utc = None
                    try:
                        is_managed = general_info.get('managed')
                        if is_managed is not None:
                            device.is_managed = is_managed == 'true'
                    except Exception:
                        logger.exception(f'Problem getting is managed for {general_info}')
                    try:
                        last_enrolled_date_utc = parse_date(general_info.get('last_enrolled_date_utc'))
                    except Exception:
                        logger.exception(f"Problem handling last enrolled update utc")
                        last_enrolled_date_utc = None

                    try:
                        lost_location_utc = parse_date((device_raw.get('security') or {}).get('lost_location_utc'))
                    except Exception:
                        logger.exception(f"Problem pasring lost location utc")
                        lost_location_utc = None
                    device_last_seen = None
                    if last_inventory_update_utc and lost_location_utc:
                        device_last_seen = max(last_inventory_update_utc, lost_location_utc)
                    elif last_inventory_update_utc:
                        device_last_seen = last_inventory_update_utc
                    elif lost_location_utc:
                        device_last_seen = lost_location_utc
                    if last_enrolled_date_utc and device_last_seen:
                        device_last_seen = max(device_last_seen, last_enrolled_date_utc)
                    elif last_enrolled_date_utc:
                        device_last_seen = last_enrolled_date_utc
                    if device_last_seen:
                        device.last_seen = device_last_seen
                    try:
                        total_size = general_info.get('capacity_mb')
                        if total_size:
                            total_size = int(total_size) / 1024.0
                        free_size = general_info.get('available_mb')
                        if free_size:
                            free_size = int(free_size) / 1024.0
                        if any([free_size, total_size]):
                            device.add_hd(total_size=total_size, free_size=free_size)
                    except Exception:
                        logger.exception(f"Problem parsing harddrive total & free size of mobile device")

                    device.figure_os(' '.join([general_info.get('os_type', ''),
                                               general_info.get('os_version', '')]))
                    device.os.build = general_info.get('os_build', '')
                    device.phone_number = general_info.get('phone_number') or None

                    try:
                        device.add_nic(general_info.get('wifi_mac_address', ''), [general_info.get('ip_address', '')])
                        device.add_nic(general_info.get('bluetooth_mac_address', ''))
                    except Exception:
                        logger.exception(f"Problem parsing nic's of mobile device")

                    device.device_model = general_info.get('model_identifier')
                    device.device_model_family = general_info.get('model')
                    device.imei = (device_raw.get('network') or {}).get('imei')
                    applications = (device_raw.get('applications') or {}).get('application', [])
                    profiles = (device_raw.get('configuration_profiles') or {}).get('configuration_profile', [])
                    profiles = [profiles] if type(profiles) != list else profiles
                    for profile in profiles:
                        try:
                            device.profiles.append(JamfProfile(**profile))
                        except Exception:
                            logger.exception(f"Unexpected profile {profile}")
                applications = [applications] if type(applications) != list else applications
                for app in applications:
                    try:
                        app_name = app.get('name', app.get('application_name', '')) or ''
                        if app_name.lower().endswith('.app'):
                            # We don't nee the .app, it can make vulnerability assessment not find vulns.
                            app_name = app_name[:-len('.app')]
                        device.add_installed_software(
                            name=app_name,
                            version=app.get('version', app.get('application_version', ''))
                        )
                    except Exception:
                        logger.exception(f"Problem adding app {str(app)} to device")

                device.set_raw(device_raw)
            except Exception:
                logger.exception(f"error parsing device {device_raw}")
                continue
            yield device

    def _correlation_cmds(self):
        """
        Correlation commands for Jamf
        :return: shell commands that help correlations
        """

        logger.error("correlation_cmds is not implemented for jamf adapter")
        raise NotImplementedError("correlation_cmds is not implemented for jamf adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        Parses (very easily) the correlation cmd result, or None if failed
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        logger.error("_parse_correlation_results is not implemented for jamf adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for jamf adapter")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.MDM]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    "name": "fetch_department",
                    "title": "Should Find Department Of Users",
                    "type": "bool"
                },
                {
                    'name': 'should_fetch_policies',
                    'type': 'bool',
                    'title': 'Should Fetch Policies'
                },
                {
                    'name': 'num_of_threads',
                    'type': 'number',
                    'title': 'Number of parallel requests to the server'
                },
                {
                    'name': 'should_not_keepalive',
                    'type': 'bool',
                    'title': 'Close connections immediately (no keep-alive)'
                },
                {
                    'name': 'threads_time_sleep',
                    'type': 'number',
                    'title': 'Seconds to sleep before sending https requests'
                }
            ],
            "required": [
                'fetch_department',
                'should_fetch_policies',
                'num_of_threads',
                'should_not_keepalive'
            ],
            "pretty_name": "Jamf Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_department': consts.DEFAULT_FETCH_DEPARTMENT,
            'should_fetch_policies': consts.DEFAULT_SHOULD_FETCH_POLICIES,
            'num_of_threads': consts.DEFAULT_NUM_OF_THREADS,
            'should_not_keepalive': consts.DEFAULT_SHOULD_NOT_KEEPALIVE,
            'threads_time_sleep': consts.DEFAULT_THREADS_TIME_SLEEP
        }

    def _on_config_update(self, config):
        logger.info(f"Loading Jamf config: {config}")
        self.__fetch_department = config.get('fetch_department', consts.DEFAULT_FETCH_DEPARTMENT)
        self.__should_fetch_policies = config.get('should_fetch_policies', consts.DEFAULT_SHOULD_FETCH_POLICIES)
        self.__num_of_simultaneous_devices = config.get('num_of_threads', consts.DEFAULT_NUM_OF_THREADS)
        self.__should_not_keepalive = config.get('should_not_keepalive', consts.DEFAULT_SHOULD_NOT_KEEPALIVE)
        self.__threads_time_sleep = config.get('threads_time_sleep', consts.DEFAULT_THREADS_TIME_SLEEP)
