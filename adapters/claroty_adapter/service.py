import logging

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from claroty_adapter.connection import ClarotyConnection

logger = logging.getLogger(f'axonius.{__name__}')


class ClarotyAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        asset_type = Field(str, 'Asset Type')
        vendor = Field(str, 'Vendor')
        criticality = Field(str, 'Criticality')
        site_name = Field(str, 'Site Name')
        ghost = Field(bool, 'Ghost')
        firmware_version = Field(str, 'Firmware Version')
        subnet_tag = Field(str, 'Subnet Tag')
        vlans = Field(str, 'Vlans')
        virtual_zone = Field(str, 'Virtual Zone')
        risk_level = Field(int, 'Risk Level')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            connection = ClarotyConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                           username=client_config['username'], password=client_config['password'],
                                           )
            with connection:
                pass  # check that the connection credentials are valid
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
        The schema ClarotyAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Claroty Domain',
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

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if not device_id:
                    logger.error(f'Problem getting id for {device_raw}')
                    continue
                name = device_raw.get('name')
                device.id = str(device_id) + (name or '')
                if name:
                    if name.endswith(' (external)'):
                        name = name[:-len(' (external)')]
                    elif name.endswith(' (external) (ghost)'):
                        name = name[:-len(' (external) (ghost)')]
                    if name == device_raw.get('ipv4') or name == device_raw.get('ipv6'):
                        name = None
                    device.name = name
                try:
                    ips = (device_raw.get('ipv4') or [])
                except Exception:
                    logger.exception(f'Problem getting IPs for {device_raw}')
                    ips = []
                try:
                    ips.extend(device_raw.get('ipv6') or [])
                except Exception:
                    logger.exception(f'Problem getting ipv6 for {device_raw}')
                try:
                    macs = device_raw.get('mac') or []
                    macs = list(macs)
                except Exception:
                    logger.exception(f'Problem getting mac for {device_raw}')
                    macs = []
                device.add_ips_and_macs(macs, ips)
                try:
                    device.last_seen = parse_date(device_raw.get('last_seen'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                try:
                    device.figure_os(device_raw.get('os'))
                except Exception:
                    logger.exception(f'Problem getting os for {device_raw}')
                asset_type = device_raw.get('asset_type__')
                if isinstance(asset_type, str) and len(asset_type) > 1 and asset_type.startswith('e'):
                    asset_type = asset_type[1:]
                device.asset_type = asset_type
                device.vendor = device_raw.get('vendor')
                device.site_name = device_raw.get('site_name')
                device.device_serial = device_raw.get('serial_number')
                device.device_model = device_raw.get('model')
                device.firmware_version = device_raw.get('firmware')
                device.virtual_zone = device_raw.get('virtual_zone_name')
                criticality = device_raw.get('criticality__')
                if isinstance(criticality, str) and len(criticality) > 1 and criticality.startswith('e'):
                    criticality = criticality[1:]
                device.criticality = criticality
                device.subnet_tag = device_raw.get('subnet_tag')
                try:
                    if isinstance(device_raw.get('vlan'), list):
                        device.vlans = device_raw.get('vlan')
                except Exception:
                    logger.exception(f'Problem with VLAN for {device_raw}')
                if isinstance(device_raw.get('ghost'), bool):
                    device.ghost = device_raw.get('ghost')
                if isinstance(device_raw.get('risk_level'), int):
                    device.risk_level = device_raw.get('risk_level')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Claroty Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Network]

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        To be implemented by inheritors, otherwise leave empty.
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        raise NotImplementedError()
