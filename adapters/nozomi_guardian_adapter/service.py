import ipaddress
import logging

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapterVlan
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import normalize_mac
from nozomi_guardian_adapter.connection import NozomiGuardianConnection
from nozomi_guardian_adapter.client_id import get_client_id
from nozomi_guardian_adapter.structures import NozomiAssetDevice

logger = logging.getLogger(f'axonius.{__name__}')


class NozomiGuardianAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(NozomiAssetDevice):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = NozomiGuardianConnection(domain=client_config['domain'],
                                              verify_ssl=client_config['verify_ssl'],
                                              https_proxy=client_config.get('https_proxy'),
                                              username=client_config['username'],
                                              password=client_config['password'])
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
        The schema NozomiGuardianAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Guardian Appliance Domain',
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
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
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

    # pylint: disable=too-many-branches
    def _create_device(self, device_raw):
        try:
            # noinspection PyTypeChecker
            device = self._new_device_adapter()  # type: NozomiAssetDevice
            device_id = device_raw.get('name')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            ips = device_raw.get('ip')
            if not isinstance(ips, list):
                ips = []
            macs = device_raw.get('mac_address')
            if not isinstance(macs, list):
                macs = []
            elif len(macs) > 0 and isinstance(device_raw.get('mac_address_level'), dict):
                # retrieve mac level by mac addresses, normalize it for comparison reasons
                macs_level = {normalize_mac(mac): level for mac, level
                              in device_raw.get('mac_address_level').items()}
                # keep only confirmed mac addresses
                macs = list(filter(lambda normalized_mac: macs_level.get(normalized_mac) == 'confirmed',
                                   map(normalize_mac, macs)))
            serial_number = device_raw.get('serial_number')

            device.id = device_id + '_' + (serial_number or next(iter(macs), ''))

            # make sure device_id (used for hostname and name) is not IP
            try:
                _ = ipaddress.ip_address(device_id)
                # If we got to this line - it means device_id is an ip
            except Exception:
                device.name = device_id
                device.hostname = device_id

            device.add_ips_and_macs(ips=ips, macs=macs)

            vlans = []
            for vlan_raw in (device_raw.get('vlan_id') or []):
                try:
                    vlan_id = int(vlan_raw)
                    vlans.append(DeviceAdapterVlan(tag_id=vlan_id))
                except Exception:
                    logging.error(f'Invalid vlan encountered {vlan_raw}')
            if vlans:
                device.add_nic(vlans=vlans)

            if device_raw.get('os'):
                device.figure_os(device_raw.get('os'))
            device.device_manufacturer = device_raw.get('vendor')
            device.device_serial = serial_number

            # specific fields
            device.level = device_raw.get('level')
            if isinstance(device_raw.get('roles'), list):
                device.roles = device_raw.get('roles')
            device.product_name = device_raw.get('product_name')
            if device_raw.get('firmware_version'):
                device.firmware_version = device_raw.get('firmware_version')
            if isinstance(device_raw.get('appliance_hosts'), list):
                device.appliance_hosts = device_raw.get('appliance_hosts')
            device.capture_device = device_raw.get('capture_device')
            device.asset_type = device_raw.get('asset_type')
            if isinstance(device_raw.get('protocols'), list):
                device.protocols = device_raw.get('protocols')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching NozomiGuardian Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
