import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.fields import Field
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from paloalto_panorama_adapter.connection import PaloaltoPanoramaConnection
from paloalto_panorama_adapter.client_id import get_client_id
from paloalto_panorama_adapter.consts import FIREWALL_DEVICE_TYPE, ARP_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


class PaloaltoPanoramaAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        # pylint: disable=R0902
        fw_connected = Field(str, 'Firewall Connection Status')
        fw_uptime = Field(str, 'Firewall Uptime')
        sw_version = Field(str, 'Firewall SW Version')
        app_version = Field(str, 'Firewall App Version')
        av_version = Field(str, 'Firewall AV Version')
        wildfire_version = Field(str, 'Firewall Wildfire Version')
        threat_version = Field(str, 'Firewall Threat Version')
        url_filtering_version = Field(str, 'Firewall URL Filtering Version')
        logdb_version = Field(str, 'Firewall LogDB Version')
        vpn_client_version = Field(str, 'Firewall VPN Client Version')
        vpn_disable_mode = Field(str, 'Firewall VPN Disable Mode')
        operational_mode = Field(str, 'Firewall Operational Mode')
        arp_interface = Field(str, 'Interface')
        arp_port = Field(str, 'Port')
        arp_status = Field(str, 'Status')
        arp_ttl = Field(str, 'TTL')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with PaloaltoPanoramaConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                            username=client_config['username'], password=client_config['password'],
                                            ) as connection:
                return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
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
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema PaloaltoPanoramaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'PaloaltoPanorama Domain',
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
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_firewall_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_raw_dict = dict()
            for xml_property in device_raw:
                device_raw_dict[xml_property.tag] = xml_property.text
            serial = device_raw_dict.get('serial')
            if not serial:
                logger.warning(f'Bad device with no Serial {device_raw_dict}')
                return None
            device.id = serial
            device.device_serial = serial
            device.fw_connected = device_raw_dict.get('connected')
            device.hostname = device_raw_dict.get('hostname')
            mac = device_raw_dict.get('mac-addr')
            if not mac:
                mac = None
            ip = device_raw_dict.get('ip-address')
            if ip:
                ips = [ip]
                device.hostname = ip
            else:
                ips = None
            if mac or ips:
                device.add_nic(mac, ips)
            device.device_model = device_raw_dict.get('model')
            device.device_model_family = device_raw_dict.get('family')
            device.fw_uptime = device_raw_dict.get('uptime')
            device.operational_mode = device_raw_dict.get('operational-mode')
            device.vpn_disable_mode = device_raw_dict.get('vpn-disable-mode')
            device.vpn_client_version = device_raw_dict.get('vpnclient-package-version-version')
            device.sw_version = device_raw_dict.get('sw-version')
            device.app_version = device_raw_dict.get('app-version')
            device.av_version = device_raw_dict.get('av-version')
            device.wildfire_version = device_raw_dict.get('wildfire-version')
            device.threat_version = device_raw_dict.get('threat-version')
            device.url_filtering_version = device_raw_dict.get('url-filtering-version')
            device.logdb_version = device_raw_dict.get('logdb-version')
            device.set_raw(device_raw_dict)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Firewall Device for {device_raw}')
            return None

    def _create_arp_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_raw_dict = dict()
            for xml_property in device_raw:
                device_raw_dict[xml_property.tag] = xml_property.text
            mac = device_raw_dict.get('mac')
            if not mac:
                logger.warning(f'Bad device with no mac {device_raw_dict}')
                return None
            device.id = mac
            ip = device_raw_dict.get('ip')
            if ip:
                ips = [ip]
            else:
                ips = None
            if mac or ips:
                device.add_nic(mac, ips)
            device.arp_interface = device_raw_dict.get('interface')
            device.arp_port = device_raw_dict.get('port')
            device.arp_status = device_raw_dict.get('status')
            device.arp_ttl = device_raw_dict.get('ttl')
            device.set_raw(device_raw_dict)
            return device
        except Exception:
            logger.exception(f'Problem with fetching arp Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == FIREWALL_DEVICE_TYPE:
                device = self._create_firewall_device(device_raw)
            if device_type == ARP_TYPE:
                device = self._create_arp_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
