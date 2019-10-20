import datetime
import ipaddress
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from snow_adapter.connection import SnowConnection
from snow_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SnowAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        organization = Field(str, 'Organization')
        is_virtual = Field(bool, 'Is Virtual')
        device_status = Field(str, 'Device Status')
        last_scan_date = Field(datetime.datetime, 'Last Scan Date')
        updated_date = Field(datetime.datetime, 'Updated Date')
        updated_by = Field(str, 'Updated By')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = SnowConnection(domain=client_config['domain'],
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
        The schema SnowAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Snow Domain',
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

    # pylint: disable=too-many-branches, too-many-statements
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('Id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('name')
            device.organization = device_raw.get('Organization')
            device.device_manufacturer = device_raw.get('Manufacturer')
            device.device_model = device_raw.get('Model')
            device.figure_os(device_raw.get('OperatingSystem'))
            device.is_virtual = device_raw.get('IsVirtual')
            device.device_status = device_raw.get('Status')
            ips_raw = device_raw.get('IpAddresses').split(',')\
                if isinstance(device_raw.get('IpAddresses'), str) else None
            if not ips_raw:
                ips_raw = []
            ips = []
            for ip_raw in ips_raw:
                try:
                    ipaddress.ip_address(ip_raw)
                    ips.append(ip_raw)
                except Exception:
                    pass
            if ips:
                device.add_nic(ips=ips)
            device.last_scan_date = parse_date(device_raw.get('LastScanDate'))
            device.updated_date = parse_date(device_raw.get('UpdatedDate'))
            device.last_seen = parse_date(device_raw.get('LastScanDate'))
            device.updated_by = device_raw.get('UpdatedBy')
            domain = device_raw.get('Domain')
            if is_domain_valid(domain):
                device.domain = domain
            try:
                for nic_raw in device_raw.get('NetworkAdapters'):
                    try:
                        mac = nic_raw.get('MacAddress')
                        if not mac:
                            mac = None
                        if nic_raw.get('IpAddress') and isinstance(nic_raw.get('IpAddress'), str):
                            ips = nic_raw.get('IpAddress').split(',')
                        else:
                            ips = None
                        device.add_nic(ips=ips, mac=mac, name=nic_raw.get('Name'))
                    except Exception:
                        logger.exception(f'Problem with nics raw {nic_raw}')
            except Exception:
                logger.exception(f'Problem getting nics for {device_raw}')
            try:
                hardware_raw = device_raw.get('Hardware')
                if not isinstance(hardware_raw, dict):
                    hardware_raw = {}
                device.bios_serial = hardware_raw.get('BiosSerialNumber')
                device.bios_version = hardware_raw.get('BiosVersion')
                if isinstance(hardware_raw.get('NumberOfProcessors'), int):
                    device.number_of_processes = hardware_raw.get('NumberOfProcessors')
            except Exception:
                logger.exception(f'Problem getting hardware raw for {device_raw}')
            try:
                for app_raw in device_raw.get('application_raw'):
                    try:
                        device.add_installed_software(name=app_raw.get('Name'),
                                                      vendor=app_raw.get('ManufacturerName'))
                    except Exception:
                        logger.exception(f'Problem with app raw {app_raw}')
            except Exception:
                logger.exception(f'Problem getting apps for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Snow Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
