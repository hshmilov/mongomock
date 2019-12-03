import logging
import datetime

from axonius.fields import JsonStringFormat
from axonius.utils.parsing import (
    format_ip,
    format_mac,
)
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from cisco_ise_adapter.client_id import get_client_id
from cisco_ise_adapter.consts import (CLIENT_CONFIG_FIELDS,
                                      CLIENT_CONFIG_TITLES,
                                      FETCH_ENDPOINTS_FIELD,
                                      FETCH_ENDPOINTS_TITLE,
                                      REQUIRED_SCHEMA_FIELDS,
                                      CiscoIseDeviceType,
                                      PxGridObject)

from cisco_ise_adapter.ers_connection import CiscoIseERSConnection
from cisco_ise_adapter.pxgrid_connection import CiscoIsePxGridConnection

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-instance-attributes
class CiscoIseAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Device Type', enum=CiscoIseDeviceType)
        device_group = ListField(str, 'Device Group')
        profile_name = Field(str, 'Netowrk Device Profile Name')
        endpoint_profile = Field(str, 'Endpoint Profile')

        called_station_id = Field(str, 'Called Station ID')
        calling_station_id = Field(str, 'Calling Station ID')
        security_group = Field(str, 'Secuirty Group')
        endpoint_check_result = Field(str, 'Endpoint Check Result')
        identity_source_port_end = Field(int, 'Source Port End')
        identity_source_port_first = Field(int, 'Source Port First')
        identity_source_port_start = Field(int, 'Source Port Start')
        mdm_compliant = Field(bool, 'Mdm Compliant')
        mdm_disk_encrypted: Field(bool, 'Mdm Disk Encrypted')
        mdm_jail_broken = Field(bool, 'Mdm Jail Broken')
        mdm_pin_locked = Field(bool, 'Mdm Pin Locked')
        mdm_registered = Field(bool, 'Mdm Registered')

        nas_id = Field(str, 'Nas Identifier')
        nas_ip = Field(str, 'Nas IP Address', converter=format_ip, json_format=JsonStringFormat.ip)
        service_type = Field(str, 'ServiceType')
        ssid = Field(str, 'ssid', converter=format_mac)
        state = Field(str, 'state')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        fields = CLIENT_CONFIG_FIELDS
        domain = client_config.get(fields.domain)

        pxgrid_enabled = client_config.get(fields.pxgrid)
        ise_result = CiscoIseERSConnection.test_reachability(domain)

        if pxgrid_enabled:
            pxgrid_result = CiscoIsePxGridConnection.test_reachability(domain)
            return ise_result and pxgrid_result
        return ise_result

    def get_ers_connection(self, client_config):
        fields = CLIENT_CONFIG_FIELDS
        connection = CiscoIseERSConnection(domain=client_config[fields.domain],
                                           verify_ssl=client_config[fields.verify_ssl],
                                           https_proxy=client_config.get(fields.https_proxy),
                                           username=client_config[fields.username],
                                           password=client_config[fields.password],
                                           fetch_endpoints=self.__fetch_endpoints,
                                           client_id=self._get_client_id(client_config))
        with connection:
            pass
        return connection

    def _get_pxgrid_collection(self):
        return self._get_collection('pxgrid_creds')

    # pylint: disable=protected-access
    def get_pxgrid_connection(self, client_config):
        fields = CLIENT_CONFIG_FIELDS

        username = None
        password = None
        date_filter = None

        collection = self._get_pxgrid_collection()
        client_id = self._get_client_id(client_config)

        pxgrid_conf = collection.find_one({'client_id': client_id}, projection={'_id': False})
        if pxgrid_conf:
            pxgrid_conf = PxGridObject(**pxgrid_conf)
            username = pxgrid_conf.username
            password = pxgrid_conf.password

        if self._last_seen_timedelta:
            now = datetime.datetime.now(datetime.timezone.utc)
            date_filter = (now - self._last_seen_timedelta).replace(microsecond=0).isoformat()
            date_filter = date_filter.replace('+00:00', '') + 'Z'

        connection = CiscoIsePxGridConnection(domain=client_config[fields.domain],
                                              verify_ssl=client_config[fields.verify_ssl],
                                              https_proxy=client_config.get(fields.https_proxy),
                                              username=username,
                                              password=password,
                                              date_filter=date_filter)

        try:
            with connection:
                pass
        finally:
            username = connection._username
            password = connection._password

            if username and password:
                pxgrid_conf = PxGridObject(client_id, username, password)
                collection.update_one({'client_id': client_id},
                                      {'$set': pxgrid_conf._asdict(), },
                                      upsert=True)

        return connection
    # pylint: enable=protected-access

    def _connect_client(self, client_config):
        fields = CLIENT_CONFIG_FIELDS
        pxgrid_connection = None
        try:
            ers_connection = self.get_ers_connection(client_config)

            if client_config.get(fields.pxgrid):
                pxgrid_connection = self.get_pxgrid_connection(client_config)

            return (ers_connection, pxgrid_connection)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config[CLIENT_CONFIG_FIELDS.domain], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        ers_client = client_data[0]
        pxgrid_client = client_data[1]

        with ers_client:
            yield from ers_client.get_device_list()

        if pxgrid_client:
            with pxgrid_client:
                yield from pxgrid_client.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema CiscoIseAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': CLIENT_CONFIG_FIELDS.domain,
                    'title': CLIENT_CONFIG_TITLES.domain,
                    'type': 'string'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.username,
                    'title': CLIENT_CONFIG_TITLES.username,
                    'type': 'string'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.password,
                    'title': CLIENT_CONFIG_TITLES.password,
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.pxgrid,
                    'title': CLIENT_CONFIG_TITLES.pxgrid,
                    'type': 'bool',
                    'default': False
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.https_proxy,
                    'title': CLIENT_CONFIG_TITLES.https_proxy,
                    'type': 'string'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.verify_ssl,
                    'title': CLIENT_CONFIG_TITLES.verify_ssl,
                    'type': 'bool'
                },
            ],
            'required': REQUIRED_SCHEMA_FIELDS,
            'type': 'array',
        }

    def _create_endpoint_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('@id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            device.id = device_id
            device.device_type = CiscoIseDeviceType.EndpointDevice
            device.add_ips_and_macs(macs=[device_raw.get('mac')])
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with parsing cisco ise endpoint for {device_raw}')
            return None

    def _create_live_session_device(self, device_raw):
        """
              {'adNormalizedUser': 'hanan',
               'calledStationId': '00:04:5F:00:0F:D1',
               'callingStationId': '00:01:24:80:B3:9C',
               'ctsSecurityGroup': 'BYOD',
               'endpointCheckResult': 'none',
               'endpointProfile': 'Unknown',
               'identitySourcePortEnd': 0,
               'identitySourcePortFirst': 0,
               'identitySourcePortStart': 0,
               'ipAddresses': ['0.0.0.9'],
               'macAddress': '00:01:24:80:B3:9C',
               'mdmCompliant': False,
               'mdmDiskEncrypted': False,
               'mdmJailBroken': False,
               'mdmPinLocked': False,
               'mdmRegistered': False,
               'nasIdentifier': '10.10.10.10',
               'nasIpAddress': '192.168.1.10',
               'networkDeviceProfileName': 'Cisco',
               'providers': ['None'],
               'serviceType': 'Login',
               'ssid': '00-04-5F-00-0F-D1',
               'state': 'STARTED',
               'timestamp': '2019-11-27T11:44:02.189Z',
               'userName': 'hanan'}]}
        """
        try:
            device = self._new_device_adapter()

            mac = device_raw.get('macAddress')
            if not mac:
                logger.info('skipping device w/o mac {device_raw}')
                return None

            device.id = 'live_session_' + mac
            try:
                device.last_seen = parse_date(device_raw.get('timestamp'))
            except Exception:
                logger.exception(f'Problem getting last seen for {device_raw}')

            ip_addresses = device_raw.get('ipAddresses')
            if not ip_addresses:
                ip_addresses = None

            device.add_nic(mac=mac, ips=ip_addresses)

            device.device_type = CiscoIseDeviceType.LiveSessionDevice

            ad_user = device_raw.get('adnormalizeduser')
            user = device_raw.get('userName')
            if ad_user and user and ad_user.lower() == user.lower():
                device.last_used_users = [ad_user]
            else:
                device.last_used_users = list(filter(None, (ad_user, user)))

            device.profile_name = device_raw.get('networkDeviceProfileName')
            device.endpoint_profile = device_raw.get('endpointProfile')

            device.called_station_id = device_raw.get('calledStationId')
            device.calling_station_id = device_raw.get('callingStationId')
            device.security_group = device_raw.get('ctsSecurityGroup')
            device.endpoint_check_result = device_raw.get('endpointCheckResult')
            device.identity_source_port_end = device_raw.get('identitySourcePortEnd')
            device.identity_source_port_first = device_raw.get('identitySourcePortFirst')
            device.identity_source_port_start = device_raw.get('identitySourcePortStart')
            device.mdm_compliant = device_raw.get('mdmCompliant')
            device.mdm_jail_broken = device_raw.get('mdmJailBroken')
            device.mdm_registered = device_raw.get('mdmRegistered')
            device.nas_id = device_raw.get('nasIdentifier')
            device.nas_ip = device_raw.get('nasIpAddress')
            device.service_type = device_raw.get('serviceType')
            device.ssid = device_raw.get('ssid')
            device.state = device_raw.get('state')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with parsing cisco ise live session for {device_raw}')

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_network_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('@id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.name = device_raw.get('@name')
            device.description = device_raw.get('@description')
            try:
                for device_group in device_raw.get('NetworkDeviceGroupList', {}):
                    if not device_group:
                        continue
                    for group in device_group.get('NetworkDeviceGroup', []):
                        device.device_group.append(group)
            except Exception:
                logger.exception(f'Unable to set device group {device_raw.get("NetworkDeviceGroupList")}')
            device.profile_name = device_raw.get('profileName')
            device.device_type = CiscoIseDeviceType.NetworkDevice
            try:
                ips = []
                for iface in device_raw.get('NetworkDeviceIPList', []):
                    if not iface:
                        continue
                    ips_raw = iface.get('NetworkDeviceIP', {})
                    if not isinstance(ips_raw, list):
                        ips_raw = [ips_raw]
                    for ip_raw in ips_raw:
                        ip = ip_raw.get('ipaddress')
                        if ip:
                            ips.append(ip)
                if ips:
                    device.add_ips_and_macs(ips=ips)
            except Exception:
                logger.exception(f'Unable to set networkdeviceIPList {device_raw.get("NetworkDeviceIPList")}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CiscoIse Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_type, device_raw in devices_raw_data:
            device = None

            if device_type == CiscoIseDeviceType.NetworkDevice.name:
                device = self._create_network_device(device_raw)
            if device_type == CiscoIseDeviceType.EndpointDevice.name:
                device = self._create_endpoint_device(device_raw)
            if device_type == CiscoIseDeviceType.LiveSessionDevice.name:
                device = self._create_live_session_device(device_raw)

            if device:
                yield device

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': FETCH_ENDPOINTS_FIELD,
                    'title': FETCH_ENDPOINTS_TITLE,
                    'type': 'bool'
                },
            ],
            'required': [
                FETCH_ENDPOINTS_FIELD,
            ],
            'pretty_name': 'Cisco ISE Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            FETCH_ENDPOINTS_FIELD: False,
        }

    def _on_config_update(self, config):
        self.__fetch_endpoints = config.get(FETCH_ENDPOINTS_FIELD, False)

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
