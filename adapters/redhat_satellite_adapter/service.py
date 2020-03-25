import logging
import re

from typing import Match

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from redhat_satellite_adapter import consts
from redhat_satellite_adapter.connection import RedhatSatelliteConnection
from redhat_satellite_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class RedhatSatelliteAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        cert_name = Field(str, 'Certificate Name')
        environment = Field(str, 'Environment')
        capabilities = ListField(str, 'Capabilities')
        compute_profile = Field(str, 'Compute Profile')
        compute_resource = Field(str, 'Compute Resource')
        medium = Field(str, 'Medium')
        organization = Field(str, 'Organization')

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
        connection = RedhatSatelliteConnection(domain=client_config['domain'],
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
        The schema RedhatSatelliteAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Red Hat Satellite/Capsule Domain',
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

    # pylint: disable=too-many-statements
    def _create_device(self, device_raw):
        try:
            # noinspection PyTypeChecker
            device: RedhatSatelliteAdapter.MyDeviceAdapter = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id

            # generic fields
            device.hostname = device.name = device_raw.get('name')
            device.add_ips_and_macs(ips=[device_raw.get('ip')], macs=[device_raw.get('mac')])
            device.device_model = device_raw.get('model_name')
            device.domain = device_raw.get('domain_name')
            device.physical_location = device_raw.get('location_name')
            device.device_serial = device_raw.get('serial')
            device.uuid = device_raw.get('uuid')
            device.first_seen = parse_date(device_raw.get('created_at'))
            device.last_seen = parse_date(device_raw.get('updated_at'))

            device_arch = device_raw.get('architecture_name')
            os_components = [device_arch, device_raw.get('operatingsystem_name')]
            for version_field, software_name in consts.VERISON_FIELDS_TO_SOFTWARE_NAMES:
                version_value = device_raw.get(version_field)
                if isinstance(version_value, str):
                    device.add_installed_software(name=software_name, version=version_value, architecture=device_arch)

            # specific fields
            device.cert_name = device_raw.get('certname')
            device.environment = device_raw.get('environment_name')
            if isinstance(device_raw.get('capabilities'), list):
                device.capabilities = device_raw.get('capabilities')
            device.compute_profile = device_raw.get('compute_profile_name')
            device.compute_resource = device_raw.get('compute_resource_name')
            device.medium = device_raw.get('medium_name')
            device.organization = device_raw.get('organization_name')

            # facts
            device_facts = device_raw.get(consts.ATTR_INJECTED_FACTS)
            if isinstance(device_facts, dict):
                # Commented fields taken from https://access.redhat.com/solutions/1406003
                memory_size = device_facts.get('dmi.memory.size')
                if isinstance(memory_size, str):
                    res = re.search(r'(\d*) MB', memory_size)
                    if res:
                        device.total_physical_memory = int(res.group(1)) / 1024.0
                device.bios_version = device_facts.get('bios_version') or device_facts.get('dmi.bios.version')
                # "lscpu.cpu_family": "6",
                # "lscpu.l1i_cache": "32K",
                # "lscpu.numa_node(s)": "1",
                # "lscpu.numa_node0_cpu(s)": "0",
                # "lscpu.on-line_cpu(s)_list": "0",
                # "lscpu.socket(s)": "1",
                # "lscpu.stepping": "3",
                # "lscpu.vendor_id": "GenuineIntel",
                device.add_cpu(cores=(int(device_facts['lscpu.cpu(s)'])
                                      if isinstance(device_facts.get('lscpu.cpu(s)'), str) else None),
                               )
                adapters = {}
                for matching_field in map(consts.RE_FIELD_NET_INTERFACE_EXCEPT_LO.match,
                                          device_facts.keys()):  # type: Match
                    if not matching_field:
                        continue

                    interface_name, field_name = tuple(map(matching_field.groupdict().get,
                                                           ['interface_name', 'interface_field']))
                    if not all(isinstance(var, str) for var in [interface_name, field_name]):
                        logger.warning(f'got invalid interface {matching_field.group(0)}')
                        continue

                    adapters.setdefault(interface_name, {})[field_name] = device_facts.get(field_name)
                for adapter_name, fields in adapters.items():
                    device.add_nic(name=adapter_name,
                                   ips=[fields.get('ipv4_address'), fields.get('ipv6_address.host')],
                                   subnets=[f'{fields.get("ipv4_address")}/{fields.get("ipv4_netmask")}',
                                            f'{fields.get("ipv6_address.host")}/{fields.get("ipv6_netmask.host")}'])
                device.add_ips_and_macs(ips=[device_facts.get('network.ipv4_address')])
                device.hostname = device.hostname or device_facts.get('uname.nodename')
                os_components.append(device_facts.get('uname.version'))
                device.virtual_host = device_facts.get('virt.is_guest') == 'true'

            # now that we've collected all os_components possible, from host and its facts, figure out the os
            device.figure_os(' '.join(comp or '' for comp in os_components))

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching RedhatSatellite Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        # AUTOADAPTER - check if you need to add other properties'
        return [AdapterProperty.Assets]
