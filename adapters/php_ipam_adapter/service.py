import logging

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from php_ipam_adapter.connection import PhpIpamConnection
from php_ipam_adapter.client_id import get_client_id
from php_ipam_adapter.structures import PhpIpamDeviceInstance, PhpIpamUserInstance, Subnet, SubnetPermission
from php_ipam_adapter.consts import EXTRA_SUBNETS, ADDRESS_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class PhpIpamAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(PhpIpamDeviceInstance):
        pass

    class MyUserAdapter(PhpIpamUserInstance):
        # TBD, after testing check values and add
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
        connection = PhpIpamConnection(domain=client_config['domain'],
                                       app_id=client_config['app_id'],
                                       fetch_users=client_config.get('fetch_users') or False,
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
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

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema PhpIpamAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'phpIPAM Host Name',
                    'type': 'string'
                },
                {
                    'name': 'app_id',
                    'title': 'Application ID',
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
                    'name': 'fetch_users',
                    'title': 'Fetch Users',
                    'type': 'bool',
                    'default': False
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
                'app_id',
                'fetch_users',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    # pylint: disable=too-many-nested-blocks
    def _fill_php_ipam_subnet_permission(subnet_raw: dict, subnet: Subnet):
        try:
            if not isinstance(subnet_raw.get('permissions'), list):
                logger.warning(f'Received invalid type of permissions for subnet permissions {subnet_raw}')
                return

            permissions = []
            for permission_raw in subnet_raw.get('permissions'):
                if isinstance(permission_raw, dict):
                    permission = SubnetPermission()
                    permission.group_id = int_or_none(permission_raw.get('group_id'))
                    permission.permissions = permission_raw.get('permission')
                    permission.name = permission_raw.get('name')
                    permission.description = permission_raw.get('desc')

                    members = []
                    if isinstance(permission_raw.get('members'), list):
                        for member in permission_raw.get('members'):
                            if not (isinstance(member, dict) and
                                    isinstance(member.get('username'), str) and
                                    member.get('username')):
                                continue
                            members.append(member.get('username'))
                    permissions.append(permission)

            subnet.permissions = permissions
        except Exception:
            logger.warning(f'Failed parsing permissions for subnet {subnet_raw}')

    def _fill_php_ipam_device_subnet(self, device_raw: list, device: MyDeviceAdapter):
        try:
            subnets = []
            for subnet_raw in device_raw or []:
                subnet = Subnet()

                subnet.id = subnet_raw.get('id')
                subnet.subnet = subnet_raw.get('subnet')
                subnet.mask = subnet_raw.get('mask')
                subnet.description = subnet_raw.get('description')
                subnet.section_id = subnet_raw.get('sectionId')
                subnet.linked_subnet = subnet_raw.get('linked_subnet')
                subnet.device_id = subnet_raw.get('device_id')
                subnet.vlan_id = subnet_raw.get('vlanId')
                subnet.vrf_id = subnet_raw.get('vrfId')
                subnet.master_subnet_id = subnet_raw.get('masterSubnetId')
                subnet.name_server_id = subnet_raw.get('nameserverId')
                subnet.show_name = subnet_raw.get('showName')
                subnet.resolve_dns = subnet_raw.get('resolveDNS')
                subnet.dns_recursive = subnet_raw.get('DNSrecursive')
                subnet.dns_records = subnet_raw.get('DNSrecords')
                subnet.allow_requests = subnet_raw.get('allowRequests')
                subnet.scan_agent = subnet_raw.get('scanAgent')
                subnet.ping_subnet = subnet_raw.get('pingSubnet')
                subnet.discover_subnet = subnet_raw.get('discoverSubnet')
                subnet.is_folder = parse_bool_from_raw(subnet_raw.get('isFolder'))
                subnet.is_full = parse_bool_from_raw(subnet_raw.get('isFull'))
                subnet.tag = subnet_raw.get('tag')
                subnet.state = subnet_raw.get('state')
                subnet.firewall_address_object = subnet_raw.get('firewallAddressObject')

                if isinstance(subnet_raw.get('location'), dict) and isinstance(
                        subnet_raw.get('location').get('address'), str) and subnet_raw.get('location').get('address'):
                    subnet.location = subnet_raw.get('location').get('address')

                self._fill_php_ipam_subnet_permission(subnet_raw, subnet)

                subnets.append(subnet)

            device.subnets = subnets
        except Exception:
            logger.exception(f'Failed creating subnet instance for device {device_raw}')

    def _fill_php_ipam_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.rack_size = int_or_none(device_raw.get('rack_size'))
            device.snmp_v3_priv_pass = device_raw.get('snmp_v3_priv_pass')
            device.snmp_community = device_raw.get('snmp_community')
            device.snmp_v3_priv_protocol = device_raw.get('snmp_v3_priv_protocol')
            device.sections = device_raw.get('sections')
            device.snmp_v3_ctx_name = device_raw.get('snmp_v3_ctx_name')
            device.snmp_v3_sec_level = device_raw.get('snmp_v3_sec_level')
            device.edit_date = parse_date(device_raw.get('editDate'))
            device.rack_start = int_or_none(device_raw.get('rack_start'))
            device.snmp_version = device_raw.get('snmp_version')
            device.snmp_queries = device_raw.get('snmp_queries')
            device.snmp_v3_auth_pass = device_raw.get('snmp_v3_auth_pass')
            device.snmp_timeout = int_or_none(device_raw.get('snmp_timeout'))
            device.rack = int_or_none(device_raw.get('rack'))
            device.snmp_v3_ctx_engine_id = device_raw.get('snmp_v3_ctx_engine_id')
            device.snmp_v3_auth_protocol = device_raw.get('snmp_v3_auth_protocol')
            device.device_type = int_or_none(device_raw.get('type'))
            device.snmp_port = int_or_none(device_raw.get('snmp_port'))
            device.vendor = device_raw.get('vendor')

            if isinstance(device_raw.get(EXTRA_SUBNETS), list):
                self._fill_php_ipam_device_subnet(device_raw.get(EXTRA_SUBNETS), device)

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_address(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('hostname') or '')

            device.owner = device_raw.get('owner')
            device.description = device_raw.get('description')
            device.hostname = device_raw.get('hostname')
            device.last_seen = parse_date(device_raw.get('lastSeen'))
            device.physical_location = device_raw.get('location')

            ips = device_raw.get('ip') or []
            if isinstance(ips, str):
                ips = [ips]

            device.add_nic(mac=device_raw.get('mac'),
                           ips=ips)

            if isinstance(device_raw.get(EXTRA_SUBNETS), list):
                self._fill_php_ipam_device_subnet(device_raw.get(EXTRA_SUBNETS), device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching phpIPAM Address for {device_raw}')
            return None

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('hostname') or '')

            device.hostname = device_raw.get('hostname')
            device.physical_location = device_raw.get('location')
            device.last_seen = parse_date(device_raw.get('editDate'))
            device.device_model = device_raw.get('model')
            device.description = device_raw.get('description')

            ips = device_raw.get('ip') or []
            if isinstance(ips, str):
                ips = [ips]
            ip = device_raw.get('ip_addr') or []
            if isinstance(ip, str):
                ips.append(ip)
            elif isinstance(ip, list):
                ips.extend(ip)

            for ip in ips:
                device.add_public_ip(ip)

            device.add_nic(ips=ips)

            self._fill_php_ipam_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching phpIPAM Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw, device_type in devices_raw_data:
            if not device_raw:
                continue
            try:
                if device_type == ADDRESS_TYPE:
                    # noinspection PyTypeChecker
                    device = self._create_address(device_raw, self._new_device_adapter())
                else:
                    # noinspection PyTypeChecker
                    device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching PhpIpam Device for {device_raw}')

    @staticmethod
    def _fill_php_ipam_user_fields(user_raw: dict, user: MyUserAdapter):
        # TBD, after testing check values and add
        try:
            pass
        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        # TBD, after testing check values and add
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = user_id + '_' + (user_raw.get('username') or '')

            user.username = user_raw.get('username')
            user.mail = user_raw.get('email')
            user.last_seen = parse_date(user_raw.get('last_seen'))

            self._fill_php_ipam_user_fields(user_raw, user)

            user.set_raw(user_raw)

            return user
        except Exception:
            logger.exception(f'Problem with fetching PhpIpam User for {user_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        """
        Gets raw data and yields User objects.
        :param users_raw_data: the raw data we get.
        :return:
        """
        for user_raw in users_raw_data:
            if not user_raw:
                continue
            try:
                # noinspection PyTypeChecker
                user = self._create_user(user_raw, self._new_user_adapter())
                if user:
                    yield user
            except Exception:
                logger.exception(f'Problem with fetching PhpIpam User for {user_raw}')

    # TBD, after testing check values and add if users are included add AdapterProperty.UserManagement
    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
