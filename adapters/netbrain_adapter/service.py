import logging

from axonius.utils.dynamic_fields import put_dynamic_field
from axonius.utils.parsing import format_ip, format_ip_raw, normalize_var_name

from axonius.fields import Field, JsonStringFormat
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from netbrain_adapter.connection import NetbrainConnection
from netbrain_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class NetbrainAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        netbrain_hostname = Field(str, 'Netbrain Name')
        mgmt_ip = Field(str, 'Management IP', converter=format_ip, json_format=JsonStringFormat.ip)
        mgmt_ip_raw = Field(str, converter=format_ip_raw, hidden=True)
        mgmt_if = Field(str, 'Management Interface')
        oid = Field(str, 'SNMP System OID')
        switch_iface = Field(str, 'Connected Switch Interface',
                             description='Interface of the device that the endsystem connected to.')
        switch_host = Field(str, 'Connected Switch Hostname',
                            description='Hostname of the device that the endsystem connected to.')

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
        connection = NetbrainConnection(
            auth_id=client_config.get('auth_id'),
            tenant_id=client_config['tenant_id'],
            domain_id=client_config['domain_id'],
            domain=client_config['domain'],
            verify_ssl=client_config['verify_ssl'],
            https_proxy=client_config.get('https_proxy'),
            username=client_config['username'],
            password=client_config['password'],
            backwards_compatible=client_config.get('backwards_compatible', True),
        )
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

    # pylint: disable=C0330
    @staticmethod
    def _clients_schema():
        """
        The schema NetbrainAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'NetBrain Web API Server Host',
                    'type': 'string'
                },
                {
                    # This parameter is only required for an external user through LDAP/AD or TACACS
                    # and the value must match with the name of external authentication which the user
                    # created with admin role during system management under "User Account" section.
                    'name': 'auth_id',
                    'title': 'External Authentication ID',
                    'type': 'string'
                },
                {
                    'name': 'domain_id',
                    'title': 'NetBrain Domain ID',
                    'type': 'string'
                },
                {
                    'name': 'tenant_id',
                    'title': 'NetBrain Tenant ID',
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
                    'name': 'backwards_compatible',
                    'title': 'Use Backwards-Compatible (pre-8.01) API',
                    'description': 'Check this box when connecting to NetBrain versions earlier than v8.01'
                                   ' (this includes v8.0, and all v7.x)',
                    'default': True,
                    'type': 'bool',
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
                'verify_ssl',
                'domain_id',
                'tenant_id',
                'backwards_compatible'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-statements
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            # generic stuff
            device.id = f'{device_id}_{device_raw.get("hostname") or ""}'
            device.netbrain_hostname = device_raw.get('hostname')
            device.name = device_raw.get('name')
            hostname = device_raw.get('hostname') or ''
            if hostname.endswith('/act'):
                hostname = hostname[:-len('/act')]
            if hostname.endswith('/stby'):
                hostname = hostname[:-len('/stby')]
            if hostname.endswith('/admin'):
                hostname = hostname[:-len('/admin')]
            if hostname.endswith('/secondary'):
                hostname = hostname[:-len('/secondary')]
            if '/' in hostname and not hostname.endswith('/'):
                hostname = hostname.split('/')[-1]
            device.hostname = hostname
            device.description = device_raw.get('deviceTypeName')
            # set first and last seen if possible
            first_seen = parse_date(device_raw.get('firstDiscoverTime'))
            last_seen = parse_date(device_raw.get('lastDiscoverTime'))
            device.first_seen = parse_date(first_seen)
            device.last_seen = parse_date(last_seen)
            # add ip
            try:
                device.add_ips_and_macs(ips=device_raw.get('mgmtIP'))
                device.mgmt_ip = device_raw.get('mgmtIP')
                device.mgmt_ip_raw = device_raw.get('mgmtIP')
            except Exception as e:
                message = f'No IP for {device_raw}'
                logger.exception(message)
                # Silence exception
            device.device_manufacturer = device_raw.get('vendor')
            device.device_model = device_raw.get('model')
            try:
                gb = 1024 * 1024 * 1024  # from bytes
                device.total_physical_memory = float(device_raw.get('mem', 0)) / gb or None
            except Exception as e:
                logger.warning(f'Failed to parse device physical memory for {hostname}')
                # continue to other stuff
            device.device_serial = device_raw.get('sn')
            # specific stuff
            device.oid = device_raw.get('oid')
            # connected switch stuff
            if isinstance(device_raw.get('x_connected_switch'), dict):
                conn_switch = device_raw.get('x_connected_switch')
                device.switch_iface = conn_switch.get('interface')
                device.switch_host = conn_switch.get('hostname')

            # dynamic stuff
            try:
                self._parse_entity_dynamic(device, device_raw)
            except Exception:
                logger.warning(f'Failed to parse dynamic fields for {device_raw}', exc_info=True)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Netbrain Device for {device_raw}')
            return None

    @staticmethod
    def _parse_entity_dynamic(entity_obj, entity_raw):
        for key, val in entity_raw.items():
            try:
                if not key or not val:
                    logger.debug(f'Bad item. Key "{key}" ; Value "{val}"')
                    continue
                normalized_var_name = 'netbrain_' + normalize_var_name(key)
                field_title = 'NetBrain ' + ' '.join(
                    [word.capitalize() for word in key.split(' ')])

                put_dynamic_field(entity_obj, normalized_var_name, val, field_title)
            except Exception as e:
                logger.warning(f'Failed to add {key}:{val} to entity {entity_obj.id}: '
                               f'Got {str(e)}')
                continue

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Network]
