import logging
import re
from datetime import timedelta

from typing import Match

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from redhat_satellite_adapter import consts
from redhat_satellite_adapter.connection import RedhatSatelliteConnection
from redhat_satellite_adapter.client_id import get_client_id
from redhat_satellite_adapter.structures import RedHatSatelliteDevice

logger = logging.getLogger(f'axonius.{__name__}')


class RedhatSatelliteAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(RedHatSatelliteDevice):
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

    # pylint: disable=arguments-differ
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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(fetch_host_facts=self._fetch_host_facts,
                                                   fetch_host_packages=self._fetch_host_packages,
                                                   hosts_chunk_size=self._hosts_chunk_size,
                                                   async_chunks=self._async_chunks,)

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

    # pylint: disable=too-many-statements,too-many-locals,too-many-branches
    def _create_device(self, device_raw):
        try:
            # noinspection PyTypeChecker
            device: RedhatSatelliteAdapter.MyDeviceAdapter = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            # generic fields
            device.hostname = device.name = device_raw.get('name')
            ips = []
            if device_raw.get('ip'):
                ips.append(device_raw.get('ip'))
            if device_raw.get('ip6'):
                ips.append(device_raw.get('ip6'))
            device.add_ips_and_macs(ips=ips, macs=[device_raw.get('mac')])
            device.device_model = device_raw.get('model_name')
            device.domain = device_raw.get('domain_name')
            device.physical_location = device_raw.get('location_name')
            device.device_serial = device_raw.get('serial')
            device.uuid = device_raw.get('uuid')
            device.first_seen = parse_date(device_raw.get('created_at'))
            device.last_seen = parse_date(device_raw.get('updated_at'))
            device_arch = device_raw.get('architecture_name')
            os_components = [device_arch, device_raw.get('operatingsystem_name')]
            for version_field, software_name in consts.VERISON_FIELDS_TO_SOFTWARE_NAMES.items():
                version_value = device_raw.get(version_field)
                if isinstance(version_value, str):
                    device.add_installed_software(name=software_name, version=version_value, architecture=device_arch)

            organizational_unit = device_raw.get('organization_name')
            if isinstance(organizational_unit, str):
                organizational_unit = [organizational_unit]
            if isinstance(organizational_unit, list):
                device.organizational_unit = organizational_unit
            device.device_managed_by = device_raw.get('owner_name')

            if isinstance(device_raw.get('uptime_seconds'), int):
                device.set_boot_time(uptime=timedelta(seconds=device_raw.get('uptime_seconds')))

            device_enabled = device_raw.get('enabled')
            if isinstance(device_enabled, bool):
                device.device_disabled = not device_enabled

            try:
                # parse BMC Interface info, see more here:
                # https://access.redhat.com/documentation/en-us/red_hat_satellite/6.4/html-single/managing_hosts/index
                device.add_nic(mac=device_raw.get('sp_mac'),
                               ips=[device_raw.get('sp_ip')],
                               name=device_raw.get('sp_name'))
            except Exception:
                logger.warning(f'Failed to parse BMC interface for device_raw: {device_raw}')

            # specific fields
            device.cert_name = device_raw.get('certname')
            device.environment_name = device_raw.get('environment_name')
            device.hostgroup_title = device_raw.get('hostgroup_title')
            device.subnet_name = device_raw.get('subnet_name')
            device.ptable_name = device_raw.get('ptable_name')
            if isinstance(device_raw.get('capabilities'), list):
                device.capabilities = device_raw.get('capabilities')
            device.compute_profile = device_raw.get('compute_profile_name')
            device.compute_resource = device_raw.get('compute_resource_name')
            device.medium_name = device_raw.get('medium_name')
            device.image_name = device_raw.get('image_name')
            device.image_file = device_raw.get('image_file')
            device.global_status_label = device_raw.get('global_status_label')
            device.build_status = device_raw.get('build_status_label')
            device.puppet_status = device_raw.get('puppet_status')
            device.puppet_proxy_name = device_raw.get('puppet_proxy_name')
            device.puppet_ca_proxy_name = device_raw.get('puppet_ca_proxy_name')
            device.openscap_proxy_name = device_raw.get('openscap_proxy_name')

            content_facet = device_raw.get('content_facet_attributes')
            if content_facet and isinstance(content_facet, dict):
                kickstart_repository = content_facet.get('kickstart_repository')
                if isinstance(kickstart_repository, dict):
                    device.kickstart_repository = kickstart_repository.get('name')

                content_view = content_facet.get('content_view')
                if isinstance(content_view, dict):
                    device.content_view_name = content_view.get('name')

                lifecycle_environment = content_facet.get('lifecycle_environment')
                if isinstance(lifecycle_environment, dict):
                    device.lifecycle_environment_name = lifecycle_environment.get('name')

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

            # handle package, remove from raw to prevent bloating
            device_packages = device_raw.pop(consts.ATTR_INJECTED_PACKAGES, None)
            if isinstance(device_packages, list):
                for package in device_packages:
                    try:
                        if not (isinstance(package, dict) and package.get('nvra')):
                            logger.warning(f'got invalid package for device {device_id}: {package}')
                            continue
                        # nvra = name-version-release.arch
                        # Example: abrt-2.1.11-42.el7.x86_64
                        # Refrence: https://access.redhat.com/solutions/3099311
                        # release Reference: https://access.redhat.com/discussions/1434473
                        name, version, rest = package.get('nvra').split('-', 2)
                        if rest.endswith('.rpm'):
                            rest = rest[:-4]
                        rhel_release, arch = rest.rsplit('.', 1)
                        device.add_installed_software(name=name,
                                                      version=version,
                                                      architecture=arch,
                                                      source=rhel_release)
                    except Exception:
                        logger.warning(f'Failed adding package to device {device_id}: {package}', exc_info=True)

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
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_host_facts',
                    'title': 'Fetch host facts',
                    'type': 'bool',
                },
                {
                    'name': 'fetch_host_packages',
                    'title': 'Fetch host packages',
                    'type': 'bool',
                },
                {
                    'name': 'hosts_chunk_size',
                    'title': 'Host chunk size',
                    'description': 'Hosts fetching chunk size.',
                    'type': 'number',
                },
                {
                    'name': 'async_chunks',
                    'title': 'Number of requests to perform in parallel',
                    'type': 'number',
                },
            ],
            'required': ['fetch_host_facts',
                         'fetch_host_packages',
                         'hosts_chunk_size',
                         'async_chunks'],
            'pretty_name': 'Red Hat Satellite Configuration',
            'type': 'array',
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_host_facts': True,
            'fetch_host_packages': True,
            'hosts_chunk_size': consts.DEVICE_PER_PAGE,
            'async_chunks': consts.ASYNC_CHUNKS,
        }

    def _on_config_update(self, config):
        self._fetch_host_facts = config.get('fetch_host_facts', True)
        self._fetch_host_packages = config.get('fetch_host_packages', True)
        self._hosts_chunk_size = config.get('hosts_chunk_size') or consts.DEVICE_PER_PAGE
        self._async_chunks = config.get('async_chunks') or consts.ASYNC_CHUNKS
