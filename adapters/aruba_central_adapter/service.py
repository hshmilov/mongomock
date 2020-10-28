import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.aruba_central.connection import ArubaCentralConnection
from axonius.clients.aruba_central.consts import ACCESS_POINT_TYPE, REGIONS, SEC_IN_DAY
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none, float_or_none
from aruba_central_adapter.client_id import get_client_id
from aruba_central_adapter.structures import ArubaCentralDeviceInstance, AccessPointInstance, SwitchInstance

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class ArubaCentralAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(ArubaCentralDeviceInstance):
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
        connection = ArubaCentralConnection(domain=REGIONS.get(client_config.get('region')),
                                            customer_id=client_config.get('customer_id'),
                                            client_id=client_config.get('client_id'),
                                            client_secret=client_config.get('client_secret'),
                                            verify_ssl=client_config.get('verify_ssl'),
                                            https_proxy=client_config.get('https_proxy'),
                                            proxy_username=client_config.get('proxy_username'),
                                            proxy_password=client_config.get('proxy_password'),
                                            username=client_config.get('username'),
                                            password=client_config.get('password'))
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
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema ArubaCentralAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'region',
                    'title': 'Region',
                    'type': 'string',
                    'enum': list(REGIONS.keys())
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
                    'name': 'customer_id',
                    'title': 'Customer ID',
                    'type': 'string',
                },
                {
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string',
                },
                {
                    'name': 'client_secret',
                    'title': 'Client Secret',
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
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'region',
                'username',
                'password',
                'customer_id',
                'client_id',
                'client_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_aruba_central_access_point_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            access_point = AccessPointInstance()
            access_point.swarm_id = device_raw.get('swarm_id')
            access_point.group_name = device_raw.get('group_name')
            access_point.cluster_id = device_raw.get('cluster_id')
            access_point.deployment_mode = device_raw.get('ap_deployment_mode')
            access_point.status = device_raw.get('status')
            access_point.swarm_master = parse_bool_from_raw(device_raw.get('swarm_master'))
            access_point.down_reason = device_raw.get('down_reason')
            access_point.mesh_role = device_raw.get('mesh_role')
            access_point.mode = device_raw.get('mode')
            access_point.client_counts = int_or_none(device_raw.get('client_count'))
            access_point.ssid_count = int_or_none(device_raw.get('ssid_count'))
            access_point.modem_connected = parse_bool_from_raw(device_raw.get('modem_connected'))
            device.access_point = access_point

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_access_point_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('serial')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.name = device_raw.get('name')
            device.device_serial = device_raw.get('serial')
            device.device_model = device_raw.get('model')
            uptime = int_or_none(device_raw.get('uptime'))
            if uptime:
                device.uptime = int(uptime / SEC_IN_DAY)
            device.last_seen = parse_date(device_raw.get('last_modified'))
            device.total_physical_memory = float_or_none(device_raw.get('mem_total'))
            device.free_physical_memory = float_or_none(device_raw.get('mem_free'))

            device.add_public_ip(ip=device_raw.get('public_ip_address'))

            try:
                ip = device_raw.get('ip_address')
                subnet_mask = device_raw.get('default_gateway')
                if isinstance(subnet_mask, str):
                    subnet_mask = f'{ip}/{subnet_mask}'
                device.add_nic(mac=device_raw.get('macaddr'),
                               ips=[ip],
                               subnets=[subnet_mask])
            except Exception:
                logger.debug(f'Failed to add_nic for access point with ID {device.id}')

            self._fill_aruba_central_access_point_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching ArubaCentral switch for {device_raw}')
            return None

    @staticmethod
    def _fill_aruba_central_switch_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            switch = SwitchInstance()
            switch.group_name = device_raw.get('group_name')
            switch.status = device_raw.get('status')
            switch.mode = int_or_none(device_raw.get('mode'))
            switch.total_clients = int_or_none(device_raw.get('total_clients'))
            switch.max_power = int_or_none(device_raw.get('max_power'))
            switch.power_consumption = int_or_none(device_raw.get('power_consumption'))
            switch.fan_speed = device_raw.get('fan_speed')
            switch.temperature = device_raw.get('temperature')
            switch.site = device_raw.get('site')
            switch.switch_type = device_raw.get('switch_type')
            device.switch = switch

        except Exception:
            logger.exception(f'Failed creating instance for switch {device_raw}')

    def _create_switch_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('serial')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.name = device_raw.get('name')
            device.device_serial = device_raw.get('serial')
            device.device_model = device_raw.get('model')
            uptime = int_or_none(device_raw.get('uptime'))
            if uptime:
                device.uptime = int(uptime / SEC_IN_DAY)
            device.last_seen = parse_date(device_raw.get('updated_at'))
            device.total_physical_memory = float_or_none(device_raw.get('mem_total'))
            device.free_physical_memory = float_or_none(device_raw.get('mem_free'))

            device.add_public_ip(ip=device_raw.get('public_ip_address'))

            try:
                device.add_nic(mac=device_raw.get('macaddr'),
                               ips=[device_raw.get('ip_address')],
                               gateway=device_raw.get('default_gateway'))
            except Exception:
                logger.debug(f'Failed to add_nic for switch with ID {device.id}')

            self._fill_aruba_central_switch_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching ArubaCentral switch for {device_raw}')
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
                if device_type == ACCESS_POINT_TYPE:
                    # noinspection PyTypeChecker
                    device = self._create_access_point_device(device_raw, self._new_device_adapter())
                else:
                    # noinspection PyTypeChecker
                    device = self._create_switch_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching ArubaCentral Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Network]
