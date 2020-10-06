import logging
import re
from collections import defaultdict

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none
from hp_ilo_adapter.connection import HpIloConnection
from hp_ilo_adapter.client_id import get_client_id
from hp_ilo_adapter.structures import HPILOInstance
from hp_ilo_adapter.consts import MAC_IPV4_REGEX, MAC_IPV6_REGEX

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class HpIloAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(HPILOInstance):
        pass

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
        connection = HpIloConnection(domain=client_config['domain'],
                                     username=client_config['username'],
                                     password=client_config['password'])
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
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
        The schema HpIloAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Hostname',
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
                }
            ],
            'required': [
                'domain',
                'username',
                'password'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_hp_ilo_fields(device_raw, device_instance: MyDeviceAdapter):
        try:
            device_instance.asset_tag = device_raw.get('AssetTag')
            device_instance.indicator_led = device_raw.get('IndicatorLED')
            device_instance.power = device_raw.get('Power')
            device_instance.power_status = device_raw.get('PowerState')
            device_instance.sku = device_raw.get('SKU')
            device_instance.system_type = device_raw.get('SystemType')

            if isinstance(device_raw.get('HostCorrelation'), dict):
                device_instance.host_fqdn = device_raw.get('HostCorrelation').get('HostFQDN')
                device_instance.host_correlation_name = device_raw.get('HostCorrelation').get('HostName')

        except Exception:
            logger.exception(f'Failed parsing HP ILO instance info for device {device_raw}')

    # pylint: disable=too-many-nested-blocks, too-many-branches
    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('Id')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_raw.get('Id')) + '_' + (device_raw.get('SerialNumber') or '')

            device.bios_version = device_raw.get('BiosVersion')
            device.hostname = device_raw.get('HostName')
            device.device_manufacturer = device_raw.get('Manufacturer')
            device.device_model = device_raw.get('Model')
            device.device_serial = device_raw.get('SerialNumber')
            device.uuid = device_raw.get('UUID')
            device.name = device_raw.get('Name')
            device.description = device_raw.get('Description')

            if isinstance(device_raw.get('HostCorrelation'), dict):
                device.add_ips_and_macs(ips=device_raw.get('HostCorrelation').get('IPAddress'),
                                        macs=device_raw.get('HostCorrelation').get('HostMACAddress'))

            if isinstance(device_raw.get('MemorySummary'), dict):
                device.total_physical_memory = int_or_none(device_raw.get('MemorySummary').get('TotalSystemMemoryGiB'))

            if isinstance(device_raw.get('ProcessorSummary'), dict):
                device.total_number_of_physical_processors = int_or_none(
                    device_raw.get('ProcessorSummary').get('Count'))

            try:
                if isinstance(device_raw.get('Boot'), dict) and isinstance(
                        device_raw.get('Boot').get('UefiTargetBootSourceOverride@Redfish.AllowableValues'), list):
                    ips_by_macs = defaultdict(set)
                    for boot_info in device_raw.get('Boot').get('UefiTargetBootSourceOverride@Redfish.AllowableValues'):
                        if isinstance(boot_info, str):
                            res_ipv4 = re.findall(MAC_IPV4_REGEX, boot_info)
                            for mac, ipv4 in res_ipv4:
                                ips_by_macs[mac].add(ipv4)

                            res_ipv6 = re.findall(MAC_IPV6_REGEX, boot_info)
                            for mac, ipv6 in res_ipv6:
                                ips_by_macs[mac].add(ipv6)

                    for mac, ips in ips_by_macs.items():
                        try:
                            ips = list(ips)
                            device.add_nic(mac=mac,
                                           ips=ips)
                        except Exception:
                            logger.exception(f'Failed adding nic for {mac}, {ips}')
            except Exception:
                logger.exception(f'Failed adding nics for {device_raw.get("Boot")}')

            self._fill_hp_ilo_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching HP ILO device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for device raw data: {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
