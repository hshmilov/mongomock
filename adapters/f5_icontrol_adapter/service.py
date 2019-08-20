import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, Field
from axonius.utils.files import get_local_config_file
from f5_icontrol_adapter.connection import F5IcontrolConnection
from f5_icontrol_adapter.client_id import get_client_id
from f5_icontrol_adapter.consts import SERVER_TYPES

logger = logging.getLogger(f'axonius.{__name__}')


class F5IcontrolAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        server_type = Field(str, 'Server Type', enum=['Pool Member', 'Virtual Server'])
        pool_name = Field(str, 'Pool Name')
        pool_partition = Field(str, 'Pool Partition')
        cmp_enabled = Field(bool, 'CMP Emabled')
        enabled = Field(bool, 'Enabled')
        nat64 = Field(bool, 'nat64')
        rate_limit = Field(bool, 'Rate Limit')
        mobile_app_tunnel = Field(bool, 'Mobile App Tunnel')
        mirror = Field(bool, 'mirror')

        allow_nat = Field(bool, 'Allow Nat')
        allow_snat = Field(bool, 'Allow SNat')

        state = Field(str, 'State')
        load_balancing_mode = Field(str, 'Load Balancing Mode')

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
        connection = F5IcontrolConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          https_proxy=client_config.get('https_proxy'),
                                          username=client_config['username'],
                                          password=client_config['password'],
                                          login_provider=client_config['login_provider'])
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
        The schema F5IcontrolAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'F5 BIG-IP Domain',
                    'type': 'string'
                },
                {
                    'name': 'login_provider',
                    'title': 'Login Provider',
                    'type': 'string',
                    'default': 'tmos',
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
                'login_provider',
                'verify_ssl'
            ],
            'type': 'array'
        }
    # pylint: disable=too-many-branches

    def _create_virtual_server_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('selfLink')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.server_type = 'Virtual Server'
            device.name = device_raw.get('name')
            device.pool_partition = device_raw.get('paratition')
            device.description = device_raw.get('description')
            pool = device_raw.get('pool')
            if pool:
                pool = pool[1:].split('/', 1)[-1]
                device.pool_name = pool
            destination = device_raw.get('destination')
            port = None
            if destination:
                destination = destination[1:].split('/', 1)[-1]
                if ':' in destination:
                    destination, port = destination.split(':', 1)
                if destination:
                    device.add_ips_and_macs(ips=[destination])
            protocol = device_raw.get('ipProtocol')
            if port:
                device.add_open_port(port_id=port, protocol=protocol)

            cmp_enabled = device_raw.get('cmpEnabled')
            if cmp_enabled:
                device.cmp_enabled = cmp_enabled == 'yes'

            enabled = device_raw.get('enabled')
            if enabled is not None:
                device.enabled = enabled

            mirror = device_raw.get('mirror')
            if mirror:
                device.mirror = mirror != 'disabled'

            mobile_app_tunnel = device_raw.get('mobileAppTunnel')
            if mobile_app_tunnel:
                device.mobile_app_tunnel = mobile_app_tunnel != 'disabled'

            nat64 = device_raw.get('nat64')
            if nat64:
                device.nat64 = nat64 != 'disabled'

            rate_limit = device_raw.get('rateLimit')
            if rate_limit:
                device.rate_limit = rate_limit != 'disabled'

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching F5Icontrol virtual server for {device_raw}')
            return None

    def _create_pool_member_device(self, device_raw):
        try:
            member_raw = device_raw['member']

            device = self._new_device_adapter()
            device_id = member_raw.get('selfLink')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.server_type = 'Pool Member'
            device.pool_name = device_raw.get('name')
            device.pool_partition = device_raw.get('partition')
            ip = member_raw.get('address')
            if ip:
                device.add_ips_and_macs(ips=[ip])
            name = member_raw.get('name')
            port = None
            if ':' in name:
                name, port = name.split(':', 1)
            device.name = name
            if port:
                device.add_open_port(port_id=port)

            allow_nat = device_raw.get('allowNat')
            if allow_nat:
                device.allow_nat = allow_nat == 'yes'

            allow_snat = device_raw.get('allowSnat')
            if allow_snat:
                device.allow_snat = allow_snat == 'yes'

            rate_limit = member_raw.get('rateLimit')
            if rate_limit:
                device.rate_limit = rate_limit != 'disabled'

            device.state = member_raw.get('state')
            device.load_balancing_mode = device_raw.get('loadBalancingMode')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching F5Icontrol pool member for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        parse_callbacks = {
            SERVER_TYPES.virtual_server: self._create_virtual_server_device,
            SERVER_TYPES.pool: self._create_pool_member_device,
        }

        for device_raw in devices_raw_data:
            try:
                kind = device_raw.get('kind')
                if kind not in parse_callbacks:
                    logger.warning(f'Invalid kind {kind}')
                    continue
                device = parse_callbacks[kind](device_raw)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Failed to parse raw data {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
