import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import format_ip
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, JsonStringFormat, ListField
from jamf_adapter import consts
from jamf_adapter.connection import JamfConnection, JamfPolicy
from jamf_adapter.exceptions import JamfException
from axonius.utils.parsing import parse_date


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


class JamfAdapter(AdapterBase):
    DEFAULT_LAST_SEEN_THRESHOLD_HOURS = 720
    DEFAULT_LAST_FETCHED_THRESHOLD_HOURS = 720

    class MyDeviceAdapter(DeviceAdapter):
        public_ip = Field(str, 'IP', converter=format_ip, json_format=JsonStringFormat.ip)
        policies = ListField(JamfPolicy, "Jamf Policies")
        profiles = ListField(JamfProfile, "Jamf Profiles")
        jamf_version = Field(str, 'Jamf Version')
        site = Field(JamfSite, "Jamf Sites")
        phone_number = Field(str, 'Phone Number')
        imei = Field(str, 'IMEI')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self.num_of_simultaneous_devices = int(self.config["DEFAULT"]["num_of_simultaneous_devices"])

    def _get_client_id(self, client_config):
        return client_config['Jamf_Domain']

    def _connect_client(self, client_config):
        try:
            connection = JamfConnection(domain=client_config[consts.JAMF_DOMAIN],
                                        num_of_simultaneous_devices=self.num_of_simultaneous_devices,
                                        http_proxy=client_config.get(consts.HTTP_PROXY),
                                        https_proxy=client_config.get(consts.HTTPS_PROXY))
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
        return client_data.get_devices()

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
                device.hostname = general_info.get('name', '')
                device.id = general_info.get('udid', '')
                device.public_ip = general_info.get('ip_address')
                try:
                    site = general_info.get('site')
                    if site:
                        device.site = JamfSite(id=int(site.get('id')), name=site.get('name'))
                except Exception:
                    logger.exception(f'device site is unexpected {device_raw}')

                device.device_serial = general_info.get("serial_number")
                if 'platform' in general_info:
                    # The field 'platform' means that we are handling a computer, and not a mobile.
                    # Thus we believe the following fields will be present.
                    device.jamf_version = general_info.get('jamf_version')
                    try:
                        device.add_nic(general_info.get('mac_address', ''), [general_info.get('last_reported_ip', '')])
                        device.add_nic(general_info.get('alt_mac_address', ''))
                    except Exception:
                        logger.exception(f"Problem adding nic to Jamf {str(device_raw)}")

                    hardware = device_raw['hardware']
                    device.figure_os(' '.join([hardware.get('os_name', ''),
                                               hardware.get('os_version', ''),
                                               hardware.get('processor_architecture', '')]))
                    device.os.build = hardware.get('os_build', '')
                    device.last_seen = parse_date(general_info.get('last_contact_time_utc', ''))
                    device.device_model = hardware.get('model_identifier')
                    device.device_model_family = hardware.get('model')

                    total_ram_mb = hardware.get('total_ram_mb')
                    if total_ram_mb is not None:
                        total_ram_mb = float(total_ram_mb)
                        device.total_physical_memory = total_ram_mb / 1024.0

                    total_number_of_physical_procesors = hardware.get("number_processors")
                    if total_number_of_physical_procesors is not None:
                        device.total_number_of_physical_processors = int(total_number_of_physical_procesors)

                    total_number_of_cores = hardware.get("number_cores")
                    if total_number_of_cores is not None:
                        device.total_number_of_cores = int(total_number_of_cores)
                    processor_speed_mhz = hardware.get("processor_speed_mhz")
                    processor_type = hardware.get("processor_type")
                    if processor_speed_mhz is not None and processor_type is not None:
                        device.add_cpu(
                            name=processor_type,
                            ghz=float(processor_speed_mhz) / 1024.0
                        )
                    device.device_manufacturer = hardware.get('make')
                    device.policies = device_raw['policies']
                    device_raw['policies'] = [x.to_dict() for x in device_raw['policies']]
                    drives = ((hardware.get('storage') or {}).get('device') or [])
                    drives = [drives] if type(drives) != list else drives
                    for drive in drives:
                        try:
                            partition = drive.get('partition')
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
                    active_directory_status = hardware.get("active_directory_status", "Not Bound")
                    if active_directory_status == "Not Bound":
                        device.part_of_domain = False
                    else:
                        device.part_of_domain = True
                        device.domain = active_directory_status
                        device.hostname += "." + active_directory_status
                    applications = ((device_raw.get('software') or {}).get('applications') or {}).get('application', [])
                else:
                    last_inventory_update_utc = parse_date(general_info.get('last_inventory_update_utc', ''))
                    lost_location_utc = parse_date((device_raw.get('security') or {}).get('lost_location_utc', ''))
                    if last_inventory_update_utc and lost_location_utc:
                        device.last_seen = max(last_inventory_update_utc, lost_location_utc)
                    elif last_inventory_update_utc:
                        device.last_seen = last_inventory_update_utc
                    elif lost_location_utc:
                        device.last_seen = lost_location_utc

                    total_size = general_info.get('capacity_mb')
                    if total_size:
                        total_size = int(total_size) / 1024.0
                    free_size = general_info.get('available_mb')
                    if free_size:
                        free_size = int(free_size) / 1024.0
                    if any([free_size, total_size]):
                        device.add_hd(total_size=total_size, free_size=free_size)

                    device.figure_os(' '.join([general_info.get('os_type', ''),
                                               general_info.get('os_version', '')]))
                    device.os.build = general_info.get('os_build', '')
                    device.phone_number = general_info.get('phone_number') or None
                    device.add_nic(general_info.get('wifi_mac_address', ''), [general_info.get('ip_address', '')])
                    device.add_nic(general_info.get('bluetooth_mac_address', ''))

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
                    device.add_installed_software(
                        name=app.get('name', app.get('application_name', '')),
                        version=app.get('version', app.get('application_version', ''))
                    )

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
        return [AdapterProperty.Agent]
