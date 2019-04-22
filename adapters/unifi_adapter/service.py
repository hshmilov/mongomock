import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import (ConnectionType, DeviceAdapter,
                                            DeviceAdapterNeighbor,
                                            DeviceAdapterNetworkInterface,
                                            DeviceAdapterOS, DeviceAdapterVlan)
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from unifi_adapter.client_id import get_client_id
from unifi_adapter.connection import UnifiConnection
from unifi_adapter.consts import (CLIENT_CONFIG_FIELDS, CLIENT_CONFIG_TITLES,
                                  DEFAULT_SITE, REQUIRED_SCHEMA_FIELDS,
                                  UnifiAdapterDeviceType)

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=too-many-instance-attributes


class UnifiAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Device Type', enum=UnifiAdapterDeviceType)
        adopted = Field(bool, 'AP Adopted')
        site_id = Field(str, 'Site ID')
        sshd_port = Field(int, 'Sshd Port')
        ap_type = Field(str, 'Unifi Device Type')
        is_wired = Field(bool, 'Is Wired')
        is_guest = Field(bool, 'is guest')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        fields = CLIENT_CONFIG_FIELDS
        domain = client_config.get(fields.domain)
        return RESTConnection.test_reachability(domain)

    @staticmethod
    def get_connection(client_config):
        fields = CLIENT_CONFIG_FIELDS
        connection = UnifiConnection(domain=client_config[fields.domain],
                                     site=client_config.get(fields.site),
                                     verify_ssl=client_config[fields.verify_ssl],
                                     https_proxy=client_config.get(fields.https_proxy),
                                     username=client_config[fields.username],
                                     password=client_config[fields.password])
        with connection:
            pass

        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
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
        The schema UnifiAdapter expects from configs

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
                    'type': 'string',
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.password,
                    'title': CLIENT_CONFIG_TITLES.password,
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.verify_ssl,
                    'title': CLIENT_CONFIG_TITLES.verify_ssl,
                    'type': 'bool'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.site,
                    'title': CLIENT_CONFIG_TITLES.site,
                    'default': DEFAULT_SITE,
                    'type': 'string'
                },
                {
                    'name': CLIENT_CONFIG_FIELDS.https_proxy,
                    'title': CLIENT_CONFIG_TITLES.https_proxy,
                    'type': 'bool'
                },
            ],
            'required': REQUIRED_SCHEMA_FIELDS,
            'type': 'array',
        }

    @staticmethod
    def _add_os(device, device_raw):
        try:
            device.os = DeviceAdapterOS()
            device.os.type = 'AirOS'

            version = device_raw.get('version').split('.')
            if len(version) > 2:
                device.os.major = version[0]
                device.os.minor = version[1]
                device.os.build = '.'.join(version[2:])
        except Exception:
            logger.exception('Failed to add os {device.get("version"}')

    @staticmethod
    def _add_nic(device, device_raw):
        try:
            ips = []
            if device_raw.get('ip'):
                ips.append(device_raw.get('ip'))
            mac = device_raw.get('mac') or None

            if mac or ips:
                device.add_nic(ips=ips, mac=mac)

        except Exception as e:
            logger.exception('Failed to add network interface')

    @staticmethod
    def _add_last_seen(device, device_raw):
        try:
            device.last_seen = datetime.datetime.fromtimestamp(device_raw.get('last_seen'))
        except Exception as e:
            logger.exception('Failed to set last seen {device_raw.get("last_seen")}')

    @staticmethod
    def _add_connected_device(device, device_raw):
        try:
            if device_raw.get('ap_mac'):
                connected_device = DeviceAdapterNeighbor()
                connected_device.connection_type = ConnectionType.Direct.name
                iface = DeviceAdapterNetworkInterface(mac=device_raw.get('ap_mac'), name=device_raw.get('essid'))
                iface.vlan_list.append(DeviceAdapterVlan(name=device_raw.get('vlan')))
                connected_device.remote_ifaces.append(iface)
                device.connected_devices.append(connected_device)

            if device_raw.get('sw_mac'):
                connected_device = DeviceAdapterNeighbor()
                connected_device.connection_type = ConnectionType.Direct.name
                iface = DeviceAdapterNetworkInterface(mac=device_raw.get('sw_mac'),
                                                      port=device_raw.get('sw_port'),
                                                      name=device_raw.get('network'))
                iface.vlan_list.append(DeviceAdapterVlan(name=device_raw.get('vlan')))
                connected_device.remote_ifaces.append(iface)
                device.connected_devices.append(connected_device)
        except Exception as e:
            logger.exception('Failed to add connected device {device_raw}')

    @staticmethod
    def _add_id(device, device_raw):
        serial = device_raw.get('serial') or None
        mac = device_raw.get('mac') or None
        _id = device_raw.get('_id') or None

        device_id_params = (_id, serial, mac)
        if not any(device_id_params):
            return False

        device.id = '_'.join(filter(None, device_id_params))
        return True

    def _create_ap_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            if not self._add_id(device, device_raw):
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            device.device_type = UnifiAdapterDeviceType.network_device

            device.name = device_raw.get('name')
            device.ap_type = device_raw.get('type')
            device.adopted = device_raw.get('adopted')
            device.device_model = device_raw.get('model')
            device.device_serial = device_raw.get('serial')
            device.site_id = device_raw.get('site_id')
            device.sshd_port = device_raw.get('sshd_port')

            self._add_os(device, device_raw)
            self._add_last_seen(device, device_raw)
            self._add_nic(device, device_raw)

            device.adapter_properties = [AdapterProperty.Network, AdapterProperty.Manager]

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Unifi Device for {device_raw}')
            return None

    def _create_client_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            if not self._add_id(device, device_raw):
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            device.device_type = UnifiAdapterDeviceType.client

            device.name = device_raw.get('hostname')
            device.is_wired = device_raw.get('is_wired')
            device.is_guest = device_raw.get('is_guest')

            self._add_last_seen(device, device_raw)
            self._add_nic(device, device_raw)
            self._add_connected_device(device, device_raw)

            device.set_raw(device_raw)
            return device

        except Exception:
            logger.exception(f'Problem with fetching Unifi Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_type, device_raw in devices_raw_data:
            device = None
            if device_type == UnifiAdapterDeviceType.client.name:
                device = self._create_client_device(device_raw)
            if device_type == UnifiAdapterDeviceType.network_device.name:
                device = self._create_ap_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
