import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.utils.datetime import parse_date
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import normalize_var_name
from infoblox_adapter.connection import InfobloxConnection
from infoblox_adapter.consts import A_TYPE, LEASE_TYPE, RESULTS_PER_PAGE, ADDRESS_TYPE, DEFAULT_FETCH_A_RECORDS, \
    DEFAULT_FETCH_USED_ADDR, DEFAULT_FETCH_LEASE

logger = logging.getLogger(f'axonius.{__name__}')


class InfobloxAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        fetch_type = Field(str, 'Infoblox Fetch Type', enum=[A_TYPE, LEASE_TYPE, ADDRESS_TYPE])
        infoblox_network_view = Field(str, 'Network View')
        infoblox_device_type = Field(str, 'Device Type')
        binding_state = Field(str, 'Lease Binding State')

        # ADDRESS_TYPE specific
        address_types = ListField(str, 'Address Types')
        address_usages = ListField(str, 'Address Usages')

        # LEASE_TYPE specific
        served_by = Field(str, 'Served By')
        start_time = Field(datetime.datetime, 'Start Time')
        end_time = Field(datetime.datetime, 'End Time')
        fingerprint = Field(str, 'Fingerprint')
        discoverer = Field(str, 'Discoverer')
        fqdn = Field(str, 'Secondary Hostname')
        network_comment = Field(str, 'Network Comment')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    def _connect_client(self, client_config):
        try:
            api_vesrion = 2.5 if client_config.get('use_api_version_25') else 2.2
            connection = InfobloxConnection(
                api_vesrion,
                domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                username=client_config['username'], password=client_config['password'],
                https_proxy=client_config.get('https_proxy')
            )
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
        Get all devices from a specific Infoblox domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Infoblox connection

        :return: A json with all the attributes returned from the Infoblox Server
        """
        date_filter = None
        try:
            if self.__use_discovered_data and self._last_seen_timedelta:
                date_filter = datetime.datetime.now(datetime.timezone.utc) - self._last_seen_timedelta
                date_filter = int(date_filter.timestamp())
        except Exception:
            logger.exception(f'Problem setting date_filter')
        with client_data:
            yield from client_data.get_device_list(
                date_filter=date_filter,
                cidr_blacklist=self.__cidr_blacklist,
                result_per_page=self.__result_per_page,
                sleep_between_requests_in_sec=self.__sleep_between_requests_in_sec,
                fetch_lease=self.__fetch_lease,
                fetch_used_addresses=self.__fetch_used_addresses,
                fetch_a_records=self.__fetch_a_records
            )

    @staticmethod
    def _clients_schema():
        """
        The schema InfobloxAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Infoblox Domain',
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
                    'name': 'use_api_version_25',
                    'title': 'Use API version 2.5',
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
                'verify_ssl',
                'use_api_version_25'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_address_device(self, device_raw, ids_set):
        try:
            device = self._new_device_adapter()
            device.fetch_type = ADDRESS_TYPE

            hostname_strip = None
            hostnames = device_raw.get('names')
            if (isinstance(hostnames, list) and
                    (len(hostnames) > 0)):
                # I did not change hostname to not change ID in many already deployed customers
                hostname_strip = hostnames[0].strip('"')
                if len(hostnames) > 1:
                    device.fqdn = hostnames[1]
            mac_address = device_raw.get('mac_address')

            if not hostname_strip and not mac_address:
                # These devices might not exist, so this log is pretty much spamming.
                logger.debug(f'No names or mac at : {device_raw}')
                return None

            try:
                device.infoblox_network_view = device_raw.get('network_view')
            except Exception:
                logger.exception(f'can not set network view: {device_raw}')

            device.hostname = hostname_strip
            if mac_address and hostname_strip:
                device_id = f'mac_{mac_address}_host_{hostname_strip}'
            elif mac_address:
                device_id = f'mac_{mac_address}'
            elif hostname_strip:
                device_id = f'host_{hostname_strip}'
            else:
                logger.error(f'Error - no mac or hostname, can not determine id: {device_raw}, continuing')
                return None
            if device_id in ids_set:
                return None
            ids_set.add(device_id)
            device.id = device_id

            ip_address = device_raw.get('ip_address')
            network = device_raw.get('network')
            try:
                device.add_nic(mac_address,
                               [ip_address] if ip_address else None,
                               subnets=[network] if network else None)
            except Exception:
                logger.exception(f'Can not set nic for device_raw: {device_raw}')

            try:
                network_data = device_raw.get('network_data') or {}
                for attr_name, attr_value_raw in (network_data.get('extattrs') or {}).items():
                    if not isinstance(attr_value_raw, dict):
                        logger.warning(f'Invalid extrattr received. {attr_value_raw}')
                        continue
                    attr_value = attr_value_raw.get('value')
                    if not attr_value:
                        continue
                    normalized_column_name = 'infoblox_' + normalize_var_name(attr_name)
                    if not device.does_field_exist(normalized_column_name):
                        # Currently we treat all columns as str
                        cn_capitalized = ' '.join([word.capitalize() for word in attr_name.split(' ')])

                        if normalized_column_name.lower() == 'infoblox_vlan':
                            field_type = int
                            device.declare_new_field(
                                f'{normalized_column_name}_str', Field(str, f'Infoblox {cn_capitalized} String'))
                        else:
                            field_type = str

                        device.declare_new_field(
                            normalized_column_name, Field(field_type, f'Infoblox {cn_capitalized}'))

                    try:
                        device[normalized_column_name] = attr_value
                    except Exception:
                        pass
                    try:
                        if normalized_column_name.lower() == 'infoblox_vlan':
                            device[f'{normalized_column_name}_str'] = attr_value
                    except Exception:
                        pass
                device.network_comment = network_data.get('comment')
            except Exception:
                logger.exception(f'Problem setting external attributes')
            try:
                binding_state = device_raw.get('lease_state')
                if binding_state in ['ABANDONED', 'FREE', 'BACKUP', 'EXPIRED', 'RELEASED']:
                    return None
                device.binding_state = binding_state
                address_types = device_raw.get('types')
                if (isinstance(address_types, list) and
                        all(isinstance(addr_type, str) for addr_type in address_types)):
                    device.address_types = address_types
                address_usages = device_raw.get('usage')
                if (isinstance(address_usages, list) and
                        all(isinstance(addr_usage, str) for addr_usage in address_usages)):
                    device.address_usages = address_usages
            except Exception:
                logger.exception(f'Failed setting address specific fields')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Infoblox Device: {device_raw}')
            return None

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_lease_device(self, device_raw, ids_set):
        try:
            device = self._new_device_adapter()
            device.fetch_type = LEASE_TYPE
            hostname = device_raw.get('client_hostname')
            if hostname:
                # I did not change hostname to not change ID in many already deployed customers
                hostname_strip = hostname.strip('"')
            else:
                hostname_strip = None
            mac_address = device_raw.get('hardware')

            if not hostname and not mac_address:
                # These devices might not exist, so this log is pretty much spamming.
                logger.debug(f'No names or mac at : {device_raw}')
                return None

            try:
                device.infoblox_network_view = device_raw.get('network_view')
            except Exception:
                logger.exception(f'can not set network view: {device_raw}')

            device.hostname = hostname_strip
            if mac_address and hostname:
                device_id = f'mac_{mac_address}_host_{hostname}'
            elif mac_address:
                device_id = f'mac_{mac_address}'
            elif hostname:
                device_id = f'host_{hostname}'
            else:
                logger.error(f'Error - no mac or hostname, can not determine id: {device_raw}, continuing')
                return None
            if device_id in ids_set:
                return None
            ids_set.add(device_id)
            device.id = device_id

            ip_address = device_raw.get('address')
            network = device_raw.get('network')
            device.fingerprint = device_raw.get('fingerprint')
            binding_state = device_raw.get('binding_state')
            if binding_state in ['ABANDONED', 'FREE', 'BACKUP', 'EXPIRED', 'RELEASED']:
                return None
            device.binding_state = binding_state
            try:
                device.add_nic(mac_address,
                               [ip_address] if ip_address else None,
                               subnets=[network] if network else None)
            except Exception:
                logger.exception(f'Can not set nic for device_raw: {device_raw}')

            try:
                device.served_by = device_raw.get('served_by')
            except Exception:
                logger.exception(f'Problem getting served by')
            end_time = None
            try:
                end_time = device_raw.get('ends')
                if end_time:
                    device.end_time = datetime.datetime.fromtimestamp(end_time)
                    device.last_seen = datetime.datetime.fromtimestamp(end_time)
            except Exception:
                logger.exception(f'Problem getting end time {end_time}')

            try:
                start_time = device_raw.get('starts')
                if start_time:
                    device.start_time = datetime.datetime.fromtimestamp(start_time)
                    if not end_time or self.__use_start_time_last_seen:
                        device.last_seen = datetime.datetime.fromtimestamp(start_time)
            except Exception:
                logger.exception(f'Problem getting start time {start_time}')

            try:
                network_data = device_raw.get('network_data') or {}
                for attr_name, attr_value_raw in (network_data.get('extattrs') or {}).items():
                    attr_value = attr_value_raw.get('value')
                    if not attr_value:
                        continue
                    normalized_column_name = 'infoblox_' + normalize_var_name(attr_name)
                    if not device.does_field_exist(normalized_column_name):
                        # Currently we treat all columns as str
                        cn_capitalized = ' '.join([word.capitalize() for word in attr_name.split(' ')])

                        if normalized_column_name.lower() == 'infoblox_vlan':
                            field_type = int
                            device.declare_new_field(
                                f'{normalized_column_name}_str', Field(str, f'Infoblox {cn_capitalized} String'))
                        else:
                            field_type = str

                        device.declare_new_field(
                            normalized_column_name, Field(field_type, f'Infoblox {cn_capitalized}'))

                    try:
                        device[normalized_column_name] = attr_value
                    except Exception:
                        pass
                    try:
                        if normalized_column_name.lower() == 'infoblox_vlan':
                            device[f'{normalized_column_name}_str'] = attr_value
                    except Exception:
                        pass
                device.network_comment = network_data.get('comment')
            except Exception:
                logger.exception(f'Problem setting external attributes')
            try:
                discovered_data = device_raw.get('discovered_data')
                if isinstance(discovered_data, dict):
                    device.last_seen = parse_date(discovered_data.get('last_discovered'))
                    device.first_seen = parse_date(discovered_data.get('first_discovered'))
                    device.figure_os(discovered_data.get('os'))
                    device.discoverer = discovered_data.get('discoverer')
                    device.infoblox_device_type = discovered_data.get('device_type')
                    device.device_manufacturer = discovered_data.get('device_vendor')
            except Exception:
                logger.exception(f'Problem with discovered data for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Infoblox Device: {device_raw}')
            return None

    def _create_a_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('name')
            device.fetch_type = A_TYPE
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.hostname = device_id
            device.id = f'A_RECORD_{device_id}'
            ip = device_raw.get('ipv4addr')
            if isinstance(ip, str) and ip:
                device.add_nic(ips=ip.split(','))
            try:
                discovered_data = device_raw.get('discovered_data')
                if isinstance(discovered_data, dict):
                    discoverer = discovered_data.get('discoverer')
                    if (self.__ignore_netmri_a_records is True and
                            isinstance(discoverer, str) and
                            discoverer.lower() == 'netmri'):
                        logger.info(f'ignoring device {device_id} discovered by NetMRI')
                        return None
                    device.discoverer = discoverer
                    device.last_seen = parse_date(discovered_data.get('last_discovered'))
                    device.first_seen = parse_date(discovered_data.get('first_discovered'))
                    device.figure_os(discovered_data.get('os'))
                    device.infoblox_device_type = discovered_data.get('device_type')
                    device.device_manufacturer = discovered_data.get('device_vendor')
                    mac = discovered_data.get('mac_address')
                    if mac:
                        device.add_nic(mac=mac)
                    if discovered_data.get('discovered_name') != 'unknown':
                        device.hostname = discovered_data.get('discovered_name')
            except Exception:
                logger.exception(f'Problem with discovered data for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Infoblox A Device: {device_raw}')
            return None

    # pylint: disable=R0912,R0915, too-many-nested-blocks, too-many-locals
    def _parse_raw_data(self, devices_raw_data):
        ids_set = set()
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == LEASE_TYPE:
                device = self._create_lease_device(device_raw, ids_set)
            elif device_type == ADDRESS_TYPE:
                device = self._create_address_device(device_raw, ids_set)
            elif device_type == A_TYPE:
                device = self._create_a_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'cidr_blacklist',
                    'title': 'CIDR exclude list',
                    'type': 'string'
                },
                {
                    'name': 'use_discovered_data',
                    'title': 'Filter results by the Discovered Data field',
                    'type': 'bool'
                },
                {
                    'name': 'result_per_page',
                    'title': 'Results per page',
                    'type': 'integer'
                },
                {
                    'name': 'sleep_between_requests_in_sec',
                    'type': 'integer',
                    'title': 'Time in seconds to sleep between each request'
                },
                {
                    'name': 'fetch_lease',
                    'type': 'bool',
                    'title': 'Fetch lease information'
                },
                {
                    'name': 'fetch_used_addresses',
                    'type': 'bool',
                    'title': 'Fetch used addresses information'
                },
                {
                    'name': 'fetch_a_records',
                    'type': 'bool',
                    'title': 'Fetch A records'
                },
                {
                    'name': 'ignore_netmri_a_records',
                    'type': 'bool',
                    'title': 'Ignore A records discovered by NetMRI'
                },
                {
                    'name': 'use_start_time_last_seen',
                    'type': 'bool',
                    'title': 'Use start time as last seen'
                }
            ],
            'required': [
                'use_discovered_data',
                'result_per_page',
                'fetch_lease',
                'fetch_used_addresses',
                'fetch_a_records',
                'ignore_netmri_a_records',
                'use_start_time_last_seen'
            ],
            'pretty_name': 'Infoblox Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'cidr_blacklist': None,
            'use_discovered_data': False,
            'result_per_page': RESULTS_PER_PAGE,
            'sleep_between_requests_in_sec': None,
            'fetch_lease': DEFAULT_FETCH_LEASE,
            'fetch_used_addresses': DEFAULT_FETCH_USED_ADDR,
            'fetch_a_records': DEFAULT_FETCH_A_RECORDS,
            'ignore_netmri_a_records': False,
            'use_start_time_last_seen': False
        }

    def _on_config_update(self, config):
        self.__cidr_blacklist = config.get('cidr_blacklist')
        self.__use_discovered_data = config.get('use_discovered_data') or False
        self.__result_per_page = config.get('result_per_page') or RESULTS_PER_PAGE
        self.__sleep_between_requests_in_sec = config.get('sleep_between_requests_in_sec') or 0
        self.__fetch_lease = bool(config.get('fetch_lease'))
        self.__fetch_used_addresses = (bool(config.get('fetch_used_addresses')) or
                                       # backwards compat
                                       bool(config.get('fetch_lease_and_used_addr')))
        self.__fetch_a_records = bool(config.get('fetch_a_records'))
        self.__ignore_netmri_a_records = bool(config.get('ignore_netmri_a_records'))
        self.__use_start_time_last_seen = config.get('use_start_time_last_seen') or False
