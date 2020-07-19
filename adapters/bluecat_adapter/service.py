import datetime
import ipaddress
import logging

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.datetime import parse_date
from axonius.utils.dynamic_fields import put_dynamic_field
from axonius.utils.files import get_local_config_file
from axonius.clients.postgres.connection import PostgresConnection
from axonius.clients.postgres.consts import DEFAULT_POSTGRES_PORT
from axonius.utils.network.sockets import test_reachability_tcp
from axonius.utils.parsing import int_to_mac, format_mac
from bluecat_adapter.connection import BluecatConnection
from bluecat_adapter.consts import DEVICE_PER_PAGE
from bluecat_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')
API_CLIENT_TYPE = 'api'
SQL_CLIENT_TYPE = 'sql'


class BluecatAdapter(ScannerAdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        device_state = Field(str, 'Device State')
        device_comments = Field(str, 'Device Comments')
        location_code = Field(str, 'Location Code')
        vendor_class_identifier = Field(str, 'Vendor Class Identifier')
        lease_time = Field(datetime.datetime, 'Lease Time')
        expiry_time = Field(datetime.datetime, 'Expiry Time')
        current_dhcp_status = Field(str, 'Current DHCP Status')
        net_id = Field(int, 'Net ID')
        net_name = Field(str, 'Net Name')
        tag_id = Field(int, 'Tag ID')
        tag_near = Field(str, 'Tag Near')
        network_id = Field(int, 'Network ID')
        network_name = Field(str, 'Network Name')
        network_cidr = Field(str, 'Network CIDR')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        if client_config.get('is_direct_db_connection'):
            return test_reachability_tcp(
                client_config.get('domain'),
                client_config.get('db_port') or DEFAULT_POSTGRES_PORT
            )
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def _connect_client(client_config):
        if not client_config.get('is_direct_db_connection'):
            try:
                with BluecatConnection(
                        domain=client_config['domain'], verify_ssl=client_config.get('verify_ssl') or False,
                        username=client_config['username'], password=client_config['password'],
                ) as connection:
                    return connection, API_CLIENT_TYPE
            except RESTException as e:
                message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                    client_config['domain'], str(e))
                logger.exception(message)
                raise ClientConnectionException(message)
        else:
            try:
                with PostgresConnection(
                        host=client_config['domain'],
                        port=client_config.get('db_port') or DEFAULT_POSTGRES_PORT,
                        username=client_config['username'],
                        password=client_config['password'],
                        db_name=client_config['db_name']
                ) as connection:
                    return connection, SQL_CLIENT_TYPE
            except RESTException as e:
                message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                    client_config['domain'], str(e))
                logger.exception(message)
                raise ClientConnectionException(message)

    # pylint: disable=arguments-differ
    def _query_devices_by_client(self, client_name, client_data_and_type):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        client_data, client_type = client_data_and_type
        if client_type == API_CLIENT_TYPE:
            with client_data:
                for device in client_data.get_device_list(self.__sleep_between_requests_in_sec,
                                                          self.__get_extra_host_data,
                                                          self.__device_per_page):
                    yield device, API_CLIENT_TYPE
        elif client_type == SQL_CLIENT_TYPE:
            with client_data:
                for device in client_data.query(f'select * from ipv4_address_view'):
                    yield device, SQL_CLIENT_TYPE

    @staticmethod
    def _clients_schema():
        """
        The schema BluecatAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host',
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
                    'name': 'is_direct_db_connection',
                    'title': 'Connect To Database',
                    'type': 'bool'
                },
                {
                    'name': 'db_port',
                    'title': 'Database Port',
                    'type': 'integer'
                },
                {
                    'name': 'db_name',
                    'title': 'Database Name',
                    'type': 'string'
                }

            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl',
                'is_direct_db_connection'
            ],
            'type': 'array'
        }

    # pylint: disable=R1702,R0912,arguments-differ
    def _parse_raw_data(self, raw_data):
        for device_raw, device_type in raw_data:
            if device_type == API_CLIENT_TYPE:
                yield from self._parse_api_raw_data([device_raw])

            else:
                device = self._parse_db_raw_data(device_raw)
                if device:
                    yield device

    # pylint: disable=too-many-statements
    def _parse_db_raw_data(self, device_raw_data):
        try:
            device = self._new_device_adapter()
            device_id = device_raw_data.get('ipaddr_id')
            if not device_id:
                return None

            try:
                expire_time = parse_date(device_raw_data.get('lc_expire_time'))
                if not expire_time:
                    return None
                expire_time = expire_time.replace(tzinfo=None)
                time_before_day = (datetime.datetime.now().replace(tzinfo=None) - datetime.timedelta(days=1))
                if expire_time < time_before_day:
                    return None
            except Exception:
                logger.exception(f'Error determining expire time')

            device_state = device_raw_data.get('lc_current_dhcp_status')
            if device_state and str(device_state).upper() in ['RESERVED', 'DHCP_FREE', 'FREE', 'DHCP_RESERVED']:
                return None
            device.device_state = device_state

            ips = []
            mac = None
            try:
                ipaddr_long = device_raw_data.get('ipaddr_long1')
                if ipaddr_long:
                    device_ip = ipaddress.IPv4Address(ipaddr_long)
                    ips.append(str(device_ip))
            except Exception:
                logger.exception(f'Can not parse ip address')

            if ips:
                device.id = f'{device_id}_{str(ips[0])}'

            try:
                macaddr_long = device_raw_data.get('macad_long1')
                if macaddr_long:
                    mac = int_to_mac(macaddr_long)
            except Exception:
                logger.exception(f'Can not parse mac {mac}')

            if ips or mac:
                device.add_nic(mac=mac, ips=ips)

            device.hostname = device_raw_data.get('ipaddr_name') or device_raw_data.get('host_name')

            try:
                device.lease_time = parse_date(device_raw_data.get('lc_lease_time'))
                device.expiry_time = parse_date(device_raw_data.get('lc_expire_time'))
            except Exception:
                logger.exception(f'Can not parse lease/expire time')

            try:
                device.net_name = device_raw_data.get('net_name')
                device.tag_near = device_raw_data.get('tag_name')
                device.net_id = device_raw_data.get('net_id')
                device.tag_id = device_raw_data.get('tag_id')
            except Exception:
                logger.exception(f'Could not parse net/tag')

            device.set_raw(device_raw_data)
            return device
        except Exception:
            logger.exception(f'Failed to parse device {device_raw_data}')

        return None

    # pylint: disable=R1702,R0912, too-many-statements, inconsistent-return-statements, invalid-name, too-many-locals
    def _parse_api_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device_state = None

                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if device_id is None:
                    logger.warning(f'Bad device with no id {device_id}')
                    continue
                device.name = device_raw.get('name').split(',')[0] if device_raw.get('name') else None
                hostname = device_raw.get('dns_name')
                device.hostname = hostname
                device_properties = device_raw.get('properties')
                lease_time = None
                mac = None
                ips = None
                expire_time = None
                try:
                    if isinstance(device_properties, str) and device_properties:
                        for property_raw in \
                                [device_property.split('=')
                                 for device_property in device_properties.split('|')[:-1] if '=' in device_property]:
                            if property_raw[0] == 'address':
                                ips = [property_raw[1]]
                            elif property_raw[0] == 'macAddress':
                                mac = property_raw[1]
                            elif property_raw[0] == 'state':
                                device_state = property_raw[1]
                                device.device_state = device_state
                            elif property_raw[0] == 'comments':
                                device.device_comments = property_raw[1]
                            elif property_raw[0] == 'locationCode':
                                device.location_code = property_raw[1]
                            elif property_raw[0] == 'vendorClassIdentifier':
                                device.vendor_class_identifier = property_raw[1]
                            elif property_raw[0] == 'expiryTime':
                                expire_time = parse_date(property_raw[1])
                                device.expiry_time = expire_time
                            elif property_raw[0] == 'leaseTime':
                                lease_time = parse_date(property_raw[1])
                                device.lease_time = lease_time
                    if mac or ips:
                        device.add_nic(mac, ips)
                except Exception:
                    logger.exception(f'Problem getting properties for {device_raw}')

                formatted_mac = format_mac(mac)

                device.id = '_'.join([
                    str(device_id),
                    (device_raw.get('name') or ''),
                    (hostname or ''),
                    (formatted_mac or '')
                ])

                try:
                    if isinstance(device_properties, str) and device_properties:
                        all_properties = dict()
                        for device_property in device_properties.split('|')[:-1]:
                            device_property_split = device_property.split('=')
                            if len(device_property_split) > 1:
                                all_properties[device_property_split[0]] = '='.join(device_property_split[1:])

                        for name, value in all_properties.items():
                            put_dynamic_field(device, f'Bluecat_property_{name}', value, f'bluecat_property.{name}')
                except Exception:
                    pass

                try:
                    network_raw = device_raw.get('network') or {}
                    try:
                        network_properties = network_raw.get('properties')
                        if isinstance(network_properties, str) and network_properties:
                            for property_raw in \
                                    [network_property.split('=')
                                     for network_property in network_properties.split('|')[:-1] if
                                     '=' in network_property]:
                                if property_raw[0] == 'CIDR':
                                    device.network_cidr = property_raw[1]
                    except Exception:
                        logger.exception(f'Problem getting properties for {device_raw}')
                    device.network_id = network_raw.get('id')
                    device.network_name = network_raw.get('name')
                except Exception:
                    logger.exception(f'Could not parse network information')
                try:
                    if expire_time:
                        device.last_seen = expire_time
                    else:
                        device.last_seen = lease_time
                except Exception:
                    logger.exception(f'Problwm with last seen')
                try:
                    if expire_time:
                        expire_time = expire_time.replace(tzinfo=None)
                        time_before_day = (datetime.datetime.now().replace(tzinfo=None) - datetime.timedelta(days=1))
                        if expire_time < time_before_day:
                            continue
                    else:
                        # pylint: disable=no-else-return
                        if str(device_state).upper() not in ['STATIC', 'GATEWAY']:
                            continue
                        elif self.__drop_static_or_gateway_if_not_expirytime:
                            continue
                except Exception:
                    logger.exception(f'Error determining expire time')

                device.set_raw(device_raw)
                if str(device_state).upper() in ['RESERVED', 'DHCP_FREE', 'FREE', 'DHCP_RESERVED']:
                    continue
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Bluecat Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'sleep_between_requests_in_sec',
                    'type': 'integer',
                    'title': 'Time in seconds to sleep between each request'
                },
                {
                    'name': 'get_extra_host_data',
                    'title': 'Get extra host data',
                    'type': 'bool'
                },
                {
                    'name': 'drop_static_or_gateway_if_not_expirytime',
                    'title': 'Drop static/gateway records with no expiry time',
                    'type': 'bool'
                },
                {
                    'name': 'device_per_page',
                    'title': 'Entities per page',
                    'type': 'integer'
                }
            ],
            'required': ['get_extra_host_data', 'drop_static_or_gateway_if_not_expirytime'],
            'pretty_name': 'BlueCat Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'sleep_between_requests_in_sec': 0,
            'get_extra_host_data': True,
            'drop_static_or_gateway_if_not_expirytime': True,
            'device_per_page': DEVICE_PER_PAGE
        }

    def _on_config_update(self, config):
        self.__sleep_between_requests_in_sec = config.get('sleep_between_requests_in_sec')
        self.__get_extra_host_data = config.get('get_extra_host_data')
        self.__drop_static_or_gateway_if_not_expirytime = config.get(
            'drop_static_or_gateway_if_not_expirytime')
        self.__device_per_page = config.get('device_per_page')
