import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from sonic_wall_adapter.connection import SonicWallConnection
from sonic_wall_adapter.client_id import get_client_id
from sonic_wall_adapter.structures import SonicWallDeviceInstance, SonicWallInterfaceInstance, AccessRule
from sonic_wall_adapter.consts import IPV4_TYPE, IPV6_TYPE, MAC_TYPE, INTERFACES_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


# API Docs:
# https://www.sonicwall.com/techdocs/pdf/sonicos-6-5-monitor.pdf
# https://sonicos-api.sonicwall.com
# https://sonicos-api.sonicwall.com/#/tfa/post_tfa
class SonicWallAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(SonicWallDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _parse_int(value):
        try:
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, bool):
            return value
        return None

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = SonicWallConnection(domain=client_config['domain'],
                                         port=client_config['port'],
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

    @staticmethod
    def _clients_schema():
        """
        The schema SonicWallAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'default': 443
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
                'port',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_sonic_wall_ip_device_fields(device_raw: dict, device_type: str, device: MyDeviceAdapter):
        try:
            ips = []
            if isinstance(device_raw.get('host'), dict):
                ips.append(device_raw.get('host').get('ip'))

            subnets = []
            if isinstance(device_raw.get('network'), dict):
                if device_raw.get('network').get('subnet') and device_raw.get('network').get('mask'):
                    subnet = device_raw.get('network').get('subnet')
                    mask = device_raw.get('network').get('mask')
                    subnets.append(f'{subnet}/{mask}')

            device.add_nic(ips=ips,
                           subnets=subnets)

        except Exception:
            logger.exception(f'Failed creating {device_type} instance for device {device_raw}')

    def _fill_sonic_wall_mac_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.multi_home = self._parse_bool(device_raw.get('multi_homed'))

            mac = device_raw.get('address')
            device.add_nic(mac=mac)
        except Exception:
            logger.exception(f'Failed creating mac instance for device {device_raw}')

    def _fill_sonic_wall_interface_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            interface_instance = SonicWallInterfaceInstance()

            interface_instance.vlan = self._parse_int(device_raw.get('vlan'))
            interface_instance.tunnel = self._parse_int(device_raw.get('tunnel'))
            interface_instance.comment = device_raw.get('comment')
            interface_instance.https_redirect = self._parse_bool(device_raw.get('https_redirect'))
            interface_instance.send_icmp_fragmentation = self._parse_bool(device_raw.get('send_icmp_fragmentation'))
            interface_instance.fragment_packets = self._parse_bool(device_raw.get('fragment_packets'))
            interface_instance.auto_discovery = self._parse_bool(device_raw.get('auto_discovery'))
            interface_instance.flow_reporting = self._parse_bool(device_raw.get('flow_reporting'))
            interface_instance.multicast = self._parse_bool(device_raw.get('multicast'))
            interface_instance.cos_8021p = self._parse_bool(device_raw.get('cos_8021p'))
            interface_instance.exclude_route = self._parse_bool(device_raw.get('exclude_route'))
            interface_instance.asymmetric_route = self._parse_bool(device_raw.get('asymmetric_route'))
            interface_instance.management_traffic_only = self._parse_bool(device_raw.get('management_traffic_only'))
            interface_instance.dns_proxy = self._parse_bool(device_raw.get('dns_proxy'))
            interface_instance.shutdown_port = self._parse_bool(device_raw.get('shutdown_port'))
            interface_instance.default_8021p_cos = device_raw.get('default_8021p_cos')
            interface_instance.firewalling = self._parse_bool(device_raw.get('firewalling'))

            if isinstance(device_raw.get('management'), dict):
                interface_instance.http_management = self._parse_bool(device_raw.get('management').get('http'))
                interface_instance.https_management = self._parse_bool(device_raw.get('management').get('https'))
                interface_instance.ping_management = self._parse_bool(device_raw.get('management').get('ping'))
                interface_instance.snmp_management = self._parse_bool(device_raw.get('management').get('snmp'))
                interface_instance.ssh_management = self._parse_bool(device_raw.get('management').get('ssh'))

            if isinstance(device_raw.get('user_login'), dict):
                interface_instance.http_login = self._parse_bool(device_raw.get('user_login').get('http'))
                interface_instance.https_login = self._parse_bool(device_raw.get('user_login').get('https'))

            device.interface_ipv4 = interface_instance
        except Exception:
            logger.exception(f'Failed creating interface instance for device {device_raw}')

    # pylint: disable=too-many-nested-blocks, too-many-locals, too-many-branches, too-many-statements
    def _fill_sonic_wall_access_rule_fields(self, device_raw: list, device: MyDeviceAdapter):
        try:
            access_rules = []
            for rule in device_raw:
                if isinstance(rule, dict):
                    access_rule = AccessRule()

                    access_rule.action_from = rule.get('source')
                    access_rule.action_to = rule.get('destination')
                    access_rule.action = rule.get('action')
                    access_rule.uuid = rule.get('uuid')
                    access_rule.name = rule.get('name')
                    access_rule.comment = rule.get('comment')
                    access_rule.enable = self._parse_bool(rule.get('enable'))
                    access_rule.reflexive = self._parse_bool(rule.get('reflexive'))
                    access_rule.max_connections = self._parse_int(rule.get('max_connections'))
                    access_rule.logging = self._parse_bool(rule.get('logging'))
                    access_rule.sip = self._parse_bool(rule.get('sip'))
                    access_rule.h323 = self._parse_bool(rule.get('h323'))
                    access_rule.management = self._parse_bool(rule.get('management'))
                    access_rule.packet_monitoring = self._parse_bool(rule.get('packet_monitoring'))
                    access_rule.fragments = self._parse_bool(rule.get('fragments'))
                    access_rule.botnet_filter = self._parse_bool(rule.get('botnet_filter'))
                    access_rule.dpi = self._parse_bool(rule.get('dpi'))
                    access_rule.single_sign_on = self._parse_bool(rule.get('single_sign_on'))
                    access_rule.block_traffic = self._parse_bool(
                        rule.get('block_traffic_for_single_sign_on'))
                    access_rule.redirect_unauthenticated_users = self._parse_bool(
                        rule.get('redirect_unauthenticated_users_to_log_in'))
                    access_rule.flow_reporting = self._parse_bool(rule.get('flow_reporting'))
                    access_rule.cos_override = self._parse_bool(rule.get('cos_override'))

                    if isinstance(rule.get('source'), dict):
                        source = rule.get('source')
                        if isinstance(source.get('address'), dict):
                            source_address = source.get('address')
                            if source_address.get('any'):
                                source_name = 'Any'
                            else:
                                source_name = source_address.get('name') or source_address.get('group')
                            access_rule.source = source_name

                    if isinstance(rule.get('destination'), dict):
                        destination = rule.get('destination')
                        if isinstance(destination.get('address'), dict):
                            destination_address = destination.get('address')
                            if destination_address.get('any'):
                                destination_name = 'Any'
                            else:
                                destination_name = destination_address.get('name') or destination_address.get('group')
                            access_rule.destination = destination_name

                    if isinstance(rule.get('port'), dict):
                        port = rule.get('port')
                        if port.get('any'):
                            port_name = 'Any'
                        else:
                            port_name = port.get('name') or port.get('group')
                        access_rule.port = port_name

                    if isinstance(rule.get('service'), dict):
                        service = rule.get('service')
                        if service.get('any'):
                            service_name = 'Any'
                        else:
                            service_name = service.get('name') or service.get('group')
                        access_rule.service = service_name

                    if isinstance(rule.get('users'), dict):
                        users = rule.get('users')
                        if isinstance(users.get('included'), dict):
                            included_users = users.get('included')
                            if included_users.get('all'):
                                user = 'All'
                            elif included_users.get('guests'):
                                user = 'Guests'
                            elif included_users.get('administrator'):
                                user = 'Administrator'
                            else:
                                user = users.get('name') or users.get('group')
                            access_rule.users_included = user

                        if isinstance(users.get('excluded'), dict):
                            included_users = users.get('excluded')
                            if included_users.get('none'):
                                user = 'None'
                            elif included_users.get('guests'):
                                user = 'Guests'
                            elif included_users.get('administrator'):
                                user = 'Administrator'
                            else:
                                user = users.get('name') or users.get('group')
                            access_rule.users_excluded = user

                    if isinstance(rule.get('connection_limit'), dict):
                        connection_limit = rule.get('connection_limit')
                        if isinstance(connection_limit.get('source')):
                            access_rule.connection_source_limit = self._parse_int(
                                connection_limit.get('source').get('threshold'))
                        if isinstance(connection_limit.get('destination')):
                            access_rule.connection_destination_limit = self._parse_int(
                                connection_limit.get('destination').get(
                                    'threshold'))

                    access_rules.append(access_rule)

            device.access_rules = access_rules
        except Exception as e:
            logger.warning(f'Failed creating access rules from device {device_raw}')

    # pylint: disable=too-many-nested-blocks, too-many-branches
    def _create_interface_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            if not device_raw.get('name'):
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            # vlan only appears in the Swagger doc and not in the official PDFs
            device.id = f'{device_raw.get("name")}_{device_raw.get("vlan") or ""}'
            name = device_raw.get('name')
            device.name = name

            device.add_firewall_rule()

            ips = []
            subnets = []
            dns_servers = []
            dhcp_servers = []
            gateway = None
            mtu = device_raw.get('mtu')
            if isinstance(device_raw.get('ip_assignment'), dict):
                ip_assigmnment = device_raw.get('ip_assignment')
                if isinstance(ip_assigmnment, dict) and isinstance(ip_assigmnment.get('mode'), dict):
                    if isinstance(ip_assigmnment.get('mode').get('dhcp'), dict):
                        if ip_assigmnment.get('mode').get('dhcp').get('hostname'):
                            dhcp_servers.append(ip_assigmnment.get('mode').get('dhcp').get('hostname'))

                    if isinstance(ip_assigmnment.get('mode').get('static'), dict):
                        static = ip_assigmnment.get('mode').get('static')

                        gateway = static.get('gateway')
                        ip = static.get('ip')
                        if ip:
                            ips.append(ip)
                        if ip and static.get('netmask'):
                            subnets.append(f'{ip}/{static.get("netmask")}')
                        if isinstance(static.get('dns'), dict):
                            if static.get('dns').get('primary'):
                                dns_servers.append(static.get('dns').get('primary'))
                            if static.get('dns').get('secondary'):
                                dns_servers.append(static.get('dns').get('secondary'))
                            if static.get('dns').get('tertiary'):
                                dns_servers.append(static.get('dns').get('tertiary'))
                        if static.get('backup_ip'):
                            ips.append(static.get('backup_ip'))

            if isinstance(device_raw.get('secondary'), dict):
                if device_raw.get('secondary').get('ip'):
                    second = device_raw.get('secondary')
                    ips.append(second.get('ip'))
                    if second.get('netmask'):
                        subnets.append(f'{second.get("ip")}/{second.get("netmask")}')

            device.add_nic(ips=ips,
                           subnets=subnets,
                           name=name,
                           mtu=mtu,
                           gateway=gateway)

            device.dns_servers = dns_servers
            device.dhcp_servers = dhcp_servers

            self._fill_sonic_wall_interface_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching SonicWall Interface Device for {device_raw}')
            return None

    def _create_device(self, device_raw: dict, device_type: str, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('uuid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + f'_{device_raw.get("name") or ""}'
            device.name = device_raw.get('name')
            device.zone = device_raw.get('zone')

            if device_type in (IPV4_TYPE, IPV6_TYPE):
                self._fill_sonic_wall_ip_device_fields(device_raw, device_type, device)
            elif device_type == MAC_TYPE:
                self._fill_sonic_wall_mac_device_fields(device_raw, device)
            else:
                logger.warning(f'Unknown device type, could not create device fields {device_raw}, {device_type}')

            if isinstance(device_raw.get('access_rules'), list) and device_raw.get('access_rules'):
                self._fill_sonic_wall_access_rule_fields(device_raw.get('access_rules'), device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching SonicWall {device_type} Device for {device_raw}')
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
                if device_type == INTERFACES_TYPE:
                    # noinspection PyTypeChecker
                    device = self._create_interface_device(device_raw, self._new_device_adapter())
                else:
                    # noinspection PyTypeChecker
                    device = self._create_device(device_raw, device_type, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching SonicWall Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Firewall]
