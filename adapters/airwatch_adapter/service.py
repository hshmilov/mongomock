import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection
from airwatch_adapter.connection import AirwatchConnection
from airwatch_adapter.consts import NOT_ENROLLED_DEVICE, ENROLLED_DEVICE, DEVICE_EXTENDED_INFO_KEY

logger = logging.getLogger(f'axonius.{__name__}')


class DeviceCompliance(SmartJsonClass):
    status = Field(bool, 'Compliant Status')
    policy_name = Field(str, 'Policy Name')
    policy_detail = Field(str, 'Policy Details')
    last_compliance_check = Field(datetime.datetime, 'Last Compliance Check')
    next_compliance_check = Field(datetime.datetime, 'Next Compliance Check')


class AirwatchAdapter(AdapterBase):

    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        airwatch_type = Field(str, 'Airwatch Device Type', enum=[ENROLLED_DEVICE, NOT_ENROLLED_DEVICE])
        imei = Field(str, 'IMEI')
        phone_number = Field(str, 'Phone Number')
        udid = Field(str, 'UdId')
        friendly_name = Field(str, 'Friendly Name')
        last_enrolled_on = Field(datetime.datetime, 'Last Enrolled On')
        notes = ListField(str, 'Notes')
        device_tags = ListField(str, 'Device Tags')
        profile_name = Field(str, 'Profile Name')
        ownership = Field(str, 'Ownership')
        location_group_name = Field(str, 'Location Group Name')
        profiles = ListField(str, 'Profiles')
        security_patch_date = Field(datetime.datetime, 'Security Patch Date')
        compliance_status = Field(str, 'Compliance Status')
        compliance_summaries = ListField(DeviceCompliance, 'Compliance Summary')
        compromised_status = Field(bool, 'Compromised Status')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    def _connect_client(self, client_config):
        try:
            connection = AirwatchConnection(domain=client_config['domain'],
                                            apikey=client_config['apikey'], verify_ssl=client_config['verify_ssl'],
                                            https_proxy=client_config.get('https_proxy'),
                                            username=client_config['username'],
                                            password=client_config['password'], url_base_prefix='/api/',
                                            headers={'User-Agent': 'Fiddler',
                                                     'aw-tenant-code': client_config['apikey'],
                                                     'Accept': 'application/xml'})
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Airwatch domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Airwatch connection

        :return: A json with all the attributes returned from the Airwatch Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema AirwatchAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Airwatch Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'Https Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_not_enrolled_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            if not device_raw.get('deviceSerialNumber'):
                return None
            device.id = device_raw.get('deviceSerialNumber')
            device.airwatch_type = NOT_ENROLLED_DEVICE
            device.device_serial = device_raw.get('deviceSerialNumber')
            device.friendly_name = device_raw.get('DeviceFriendlyName')
            device.profile_name = device_raw.get('profileName')
            device.imei = device_raw.get('deviceImei')
            device.ownership = device_raw.get('deviceOwnership')
            device.device_model = device_raw.get('deviceModel')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching not enrolledd Airwatch Device {device_raw}')
            return None

    @staticmethod
    def _parse_compliance_summary(compliance_summary_raw: dict):
        if not (isinstance(compliance_summary_raw, dict) and
                isinstance(compliance_summary_raw.get('DeviceCompliance'), list)):
            return None

        compliance_summaries = []
        for device_compliance_dict in compliance_summary_raw.get('DeviceCompliance'):
            try:
                compliant_status = False
                if isinstance(device_compliance_dict.get('CompliantStatus'), bool):
                    compliant_status = device_compliance_dict.get('CompliantStatus')

                compliance_summaries.append(DeviceCompliance(
                    status=compliant_status,
                    policy_name=device_compliance_dict.get('PolicyName'),
                    policy_detail=device_compliance_dict.get('PolicyDetail'),
                    last_compliance_check=parse_date(device_compliance_dict.get('LastComplianceCheck')),
                    next_compliance_check=parse_date(device_compliance_dict.get('NextComplianceCheck')),
                ))
            except Exception:
                logger.warning(f'Failed parsing DeviceCompliance: {device_compliance_dict}')
        return compliance_summaries

    # pylint: disable=R0912,R0915
    # pylint: disable=too-many-locals,using-constant-test,too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            if device_type == NOT_ENROLLED_DEVICE:
                device = self._create_not_enrolled_device(device_raw)
                if device:
                    yield device
                continue
            try:
                device = self._new_device_adapter()
                if not device_raw.get('Id'):
                    continue
                else:
                    device_id_value = str(device_raw.get('Id').get('Value'))
                device.imei = device_raw.get('Imei')
                device.airwatch_type = ENROLLED_DEVICE
                device.device_model = device_raw.get('Model')
                device.location_group_name = device_raw.get('LocationGroupName')
                device.last_seen = parse_date(str(device_raw.get('LastSeen', '')))
                device.figure_os((device_raw.get('Platform') or '') + ' ' + (device_raw.get('OperatingSystem') or ''))
                device.phone_number = device_raw.get('PhoneNumber')
                device.email = device_raw.get('UserEmailAddress')
                try:
                    profiles_raw = device_raw.get('profiles_raw')
                    if not isinstance(profiles_raw, list):
                        profiles_raw = []
                    for profile_raw in profiles_raw:
                        if isinstance(profile_raw, dict) and profile_raw.get('Name'):
                            device.profiles.append(profile_raw.get('Name'))
                except Exception:
                    logger.warning(f'Problem getting profiles for {device_raw}')
                try:
                    network_raw = device_raw.get('Network') or {}
                    nics_raw = network_raw.get('DeviceNetworkInfo')
                    if not isinstance(nics_raw, list):
                        nics_raw = []
                    macs = []
                    for nic_raw in nics_raw:
                        if isinstance(nic_raw, dict) and nic_raw.get('ConnectionType') == 'Ethernet':
                            macs.append(nic_raw.get('MACAddress'))
                    wifi_info = network_raw.get('WifiInfo') or {}
                    mac_address = wifi_info.get('WifiMacAddress', device_raw.get('MacAddress'))
                    if not mac_address or mac_address == '0.0.0.0':
                        mac_address = None
                    else:
                        macs.append(mac_address)
                    ipaddresses_raw = network_raw.get('IPAddress') or []
                    ipaddresses = []
                    falsed_ips = ['0.0.0.0', '127.0.0.1', '', None]
                    for ipaddress_raw in ipaddresses_raw:
                        if ipaddresses_raw[ipaddress_raw] not in falsed_ips:
                            ipaddresses.append(ipaddresses_raw[ipaddress_raw])
                    if ipaddresses != [] or mac_address is not None:
                        device.add_ips_and_macs(macs=macs, ips=ipaddresses)
                except Exception:
                    logger.exception('Problem adding nic to Airwatch')
                device.device_serial = device_raw.get('SerialNumber')
                device.udid = device_raw.get('Udid')

                name = device_raw.get('DeviceFriendlyName') or ''
                username = device_raw.get('UserName')
                if username and name and name.startswith(username + ' '):
                    name = name[len(username) + 1:]
                    if ' Desktop Windows ' in name:
                        name = name[:name.index(' Desktop Windows ')]
                    if ' MacBook Pro ' in name:
                        name = name[:name.index(' MacBook Pro ')]
                    if ' iPhone iOS ' in name:
                        name = name[:name.index(' iPhone iOS ')]
                        if ' Android ' in name:
                            name = name[:name.index(' Android ')]
                    name = name.replace(' ', '-')
                    name = name.replace('\'', '')
                    name = name.replace('’', '')
                    name = name.replace('(', '')
                    name = name.replace(')', '')
                    name = name.replace('.', '-')
                device_name = name + '_' + str(device_raw.get('MacAddress'))
                device.name = device_name
                device.id = device_id_value + '_' + device_name
                device.friendly_name = device_raw.get('DeviceFriendlyName')

                device.last_enrolled_on = parse_date(device_raw.get('LastEnrolledOn'))
                try:
                    notes_raw = device_raw.get('DeviceNotes')
                    if not isinstance(notes_raw, list):
                        notes_raw = []
                    for note_raw in notes_raw:
                        if isinstance(note_raw, dict) and note_raw.get('Note'):
                            device.notes.append(note_raw.get('Note'))
                except Exception:
                    logger.exception(f'Problem getting notes for {device_raw}')
                try:
                    tags_raw = device_raw.get('DeviceTags')
                    if not isinstance(tags_raw, list):
                        tags_raw = []
                    for tag_raw in tags_raw:
                        if isinstance(tag_raw, dict) and tag_raw.get('TagName'):
                            device.device_tags.append(tag_raw.get('TagName'))
                except Exception:
                    logger.exception(f'Problem getting notes for {device_raw}')

                device.last_used_users = (device_raw.get('UserName') or '').split(',')
                try:
                    for app_raw in device_raw.get('DeviceApps', []):
                        device.add_installed_software(name=app_raw.get('ApplicationName'),
                                                      version=app_raw.get('Version'))
                except Exception:
                    logger.exception(f'Problem adding software to Airwatch {device_raw}')
                device.compliance_status = device_raw.get('ComplianceStatus')
                compliance_summaries = self._parse_compliance_summary(device_raw.get('ComplianceSummary'))
                if compliance_summaries:
                    device.compliance_summaries = compliance_summaries
                if isinstance(device_raw.get('CompromisedStatus'), bool):
                    device.compromised_status = device_raw.get('CompromisedStatus')
                try:
                    security_patch_date = parse_date(device_raw.get('SecurityPatchDate'))
                    if not security_patch_date:
                        device_extended_info = device_raw.get(DEVICE_EXTENDED_INFO_KEY)
                        if isinstance(device_extended_info, dict):
                            security_patch_date = parse_date(device_extended_info.get('SecurityPatchDate'))
                    device.security_patch_date = security_patch_date
                except Exception:
                    logger.warning(f'Failed parsing extensivesearch information for device {device_raw}', exc_info=True)

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Airwatch Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.MDM]
