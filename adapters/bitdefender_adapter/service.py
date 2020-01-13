import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from bitdefender_adapter.connection import BitdefenderConnection
from bitdefender_adapter.consts import ACCESS_URL_DEFAULT

logger = logging.getLogger(f'axonius.{__name__}')


class BitdefenderAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        is_managed = Field(bool, 'Is Managed')
        ssid = Field(str, 'SSID')
        engine_version = Field(str, 'Engine Version')
        policy_name = Field(str, 'Policy Name')
        gravityzone_label = Field(str, 'Label')
        advanced_threat_control = Field(bool, 'Advanced Threat Control')
        antimalware = Field(bool, 'Antimalware')
        content_control = Field(bool, 'Content Control')
        device_control = Field(bool, 'Device Control')
        firewall = Field(bool, 'Firewall')
        power_user = Field(bool, 'Power User')
        malware_status_detection = Field(bool, 'Malware Status Detection')
        malware_status_infected = Field(bool, 'Malware Status Infected')
        group = Field(str, 'Group')
        last_update = Field(datetime.datetime, 'Last Update')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = BitdefenderConnection(domain=client_config['domain'],
                                               verify_ssl=client_config['verify_ssl'],
                                               username=client_config['apikey'],
                                               access_url_path=client_config['access_url_path'],
                                               https_proxy=client_config.get('https_proxy'))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema the adapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Bitdefender Domain',
                    'type': 'string'
                },
                {
                    'name': 'access_url_path',
                    'type': 'string',
                    'default': ACCESS_URL_DEFAULT,
                    'title': 'Access URL Base Path'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'apikey',
                'access_url_path',
                'veirfy_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if not device_id:
                    logger.warning(f'Device with no ID {device_raw}')
                    continue
                device_id += device_raw.get('name') or ''
                device.id = device_id
                device.name = device_raw.get('name')
                device.hostname = device_raw.get('fqdn')
                device.figure_os(device_raw.get('operatingSystemVersion'))
                try:
                    ip_address = device_raw.get('ip')
                    if ip_address and isinstance(ip_address, str):
                        ip_address = ip_address.split(',')
                    else:
                        ip_address = None
                    mac_addresses = device_raw.get('macs')
                    if not isinstance(mac_addresses, list):
                        mac_addresses = None
                    device.add_ips_and_macs(mac_addresses, ip_address)
                except Exception:
                    logger.exception(f'Problem adding nic to {device_raw}')
                is_managed = device_raw.get('isManaged')
                if isinstance(is_managed, bool):
                    device.is_managed = is_managed
                device.ssid = device_raw.get('ssid')
                try:
                    extra_data_raw = device_raw.get('extra_data')
                    if not isinstance(extra_data_raw, dict):
                        extra_data_raw = {}
                    device.last_seen = parse_date(extra_data_raw.get('lastSeen'))
                    agent_raw = extra_data_raw.get('agent')
                    if not isinstance(agent_raw, dict):
                        agent_raw = {}
                    device.add_agent_version(agent=AGENT_NAMES.bitdefender,
                                             version=agent_raw.get('productVersion'))
                    device.last_update = parse_date(agent_raw.get('lastUpdate'))
                    device.engine_version = agent_raw.get('engineVersion')
                    policy_raw = extra_data_raw.get('policy')
                    if not isinstance(policy_raw, dict):
                        policy_raw = {}
                    device.policy_name = policy_raw.get('name')
                    device.gravityzone_label = extra_data_raw.get('label')
                    modules_raw = extra_data_raw.get('modules')
                    if not isinstance(modules_raw, dict):
                        modules_raw = {}
                    device.advanced_threat_control = modules_raw.get('advancedThreatControl') \
                        if isinstance(modules_raw.get('advancedThreatControl'), bool) else None
                    device.antimalware = modules_raw.get('antimalware') \
                        if isinstance(modules_raw.get('antimalware'), bool) else None
                    device.content_control = modules_raw.get('contentControl') \
                        if isinstance(modules_raw.get('contentControl'), bool) else None
                    device.device_control = modules_raw.get('deviceControl') \
                        if isinstance(modules_raw.get('deviceControl'), bool) else None
                    device.firewall = modules_raw.get('firewall') \
                        if isinstance(modules_raw.get('firewall'), bool) else None
                    device.power_user = modules_raw.get('powerUser') \
                        if isinstance(modules_raw.get('powerUser'), bool) else None
                    group_raw = extra_data_raw.get('group')
                    if not isinstance(group_raw, dict):
                        group_raw = {}
                    device.group = group_raw.get('name')
                    malware_status_raw = extra_data_raw.get('malwareStatus')
                    if not isinstance(malware_status_raw, dict):
                        malware_status_raw = {}
                    device.malware_status_detection = malware_status_raw.get('detection') \
                        if isinstance(malware_status_raw.get('detection'), bool) else None
                    device.malware_status_infected = malware_status_raw.get('infected') \
                        if isinstance(malware_status_raw.get('infected'), bool) else None

                except Exception:
                    logger.exception(f'Problem with extra data for {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Bitdefender Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
