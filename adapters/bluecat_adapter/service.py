import datetime
import ipaddress
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.clients.postgres.connection import PostgresConnection
from axonius.clients.postgres.consts import DEFAULT_POSTGRES_PORT
from axonius.utils.parsing import int_to_mac
from bluecat_adapter.connection import BluecatConnection
from bluecat_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')
API_CLIENT_TYPE = 'api'
SQL_CLIENT_TYPE = 'sql'


class BluecatAdapter(AdapterBase):
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

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

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
    @staticmethod
    def _query_devices_by_client(client_name, client_data_and_type):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        client_data, client_type = client_data_and_type
        if client_type == API_CLIENT_TYPE:
            with client_data:
                for device in client_data.get_device_list():
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

    def _parse_db_raw_data(self, device_raw_data):
        try:
            device = self._new_device_adapter()
            device_id = device_raw_data.get('ipaddr_id')
            if not device_id:
                return None

            device_state = device_raw_data.get('lc_current_dhcp_status')
            if device_state and str(device_state).upper() in ['RESERVED', 'DHCP_FREE', 'DHCP_RESERVED']:
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

    # pylint: disable=R1702,R0912
    def _parse_api_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device_state = None
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if device_id is None:
                    logger.warning(f'Bad device with no id {device_id}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('name') or '')
                device.name = device_raw.get('name').split(',')[0] if device_raw.get('name') else None
                device.hostname = device_raw.get('dns_name')
                device_properties = device_raw.get('properties')
                mac = None
                ips = None
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
                                device.expiry_time = parse_date(property_raw[1])
                            elif property_raw[0] == 'leaseTime':
                                device.lease_time = parse_date(property_raw[1])
                    if mac or ips:
                        device.add_nic(mac, ips)
                except Exception:
                    logger.exception(f'Problem getting properties for {device_raw}')
                device.set_raw(device_raw)
                if device_state in ['RESERVED', 'DHCP_FREE', 'DHCP_RESERVED']:
                    continue
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Bluecat Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
