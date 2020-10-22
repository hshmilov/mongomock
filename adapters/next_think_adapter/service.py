import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from next_think_adapter.connection import NextThinkConnection
from next_think_adapter.client_id import get_client_id
from next_think_adapter.structures import NextThinkDeviceInstance, NextThinkUserInstance
from next_think_adapter.consts import DEFAULT_WEB_API_PORT, DEFAULT_FETCH_DAYS, MAXIMUM_LAST_FETCH

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class NextThinkAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(NextThinkDeviceInstance):
        pass

    class MyUserAdapter(NextThinkUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, (bool, int)):
            return bool(value)
        return None

    @staticmethod
    def _parse_int(value):
        try:
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                port=client_config['port'],
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        if isinstance(client_config['last_fetch_data'], int) and \
                0 < client_config['last_fetch_data'] < MAXIMUM_LAST_FETCH:
            last_fetch = client_config['last_fetch_data']
        else:
            logger.debug(f'Received invalid value {client_config["last_fetch_data"]}, '
                         f'should be between 0 - {MAXIMUM_LAST_FETCH}')
            last_fetch = DEFAULT_FETCH_DAYS

        connection = NextThinkConnection(domain=client_config['domain'],
                                         port=client_config['port'],
                                         last_fetch_data=last_fetch,
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
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema NextThinkAdapter expects from configs

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
                    'default': DEFAULT_WEB_API_PORT
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
                    'name': 'last_fetch_data',
                    'title': 'Limit Fetched Data to Last x Days',
                    'description': f'Data fetch can be configured to the last 1-{MAXIMUM_LAST_FETCH} days.',
                    'type': 'integer',
                    'enum': list(range(1, MAXIMUM_LAST_FETCH + 1)),
                    'default': DEFAULT_FETCH_DAYS
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
                'last_fetch_data',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _fill_next_think_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.antispyware_name = device_raw.get('antispyware_name')
            device.antivirus_name = device_raw.get('antivirus_name')
            device.chassis_serial_number = device_raw.get('chassis_serial_number')
            device.device_password_required = self._parse_bool(device_raw.get('device_password_required'))
            device.device_product_id = device_raw.get('device_product_id')
            device.device_product_version = device_raw.get('device_product_version')
            device.distinguished_name = device_raw.get('distinguished_name')
            device.entity = device_raw.get('entity')
            device.firewall_name = device_raw.get('firewall_name')
            device.group_name = device_raw.get('group_name')

            try:
                platform = device_raw.get('platform')
                device.platform = platform
            except Exception:
                logger.debug(f'Received invalid device platform - {platform}')

            device.sid = device_raw.get('sid')

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.bios_serial = device_raw.get('bios_serial_number')
            device.device_manufacturer = device_raw.get('device_manufacturer')
            device.device_model = device_raw.get('device_model')
            device.device_serial = device_raw.get('device_serial_number')

            try:
                pc_type = device_raw.get('device_type')
                pc_type = pc_type.title()
                device.pc_type = pc_type
            except Exception:
                logger.debug(f'Received invalid device type - {pc_type}')

            device.uuid = device_raw.get('device_uuid')
            device.first_seen = parse_date(device_raw.get('first_seen'))

            ip_addresses = device_raw.get('ip_addresses')
            mac_addresses = device_raw.get('mac_addresses')
            device.add_ips_and_macs(macs=mac_addresses,
                                    ips=ip_addresses)

            last_loggged_on_user = device_raw.get('last_logged_on_user')
            if isinstance(last_loggged_on_user, str) and last_loggged_on_user:
                device.last_used_users = [last_loggged_on_user]

            local_administrators = device_raw.get('local_administrators')
            if isinstance(local_administrators, str) and local_administrators:
                device.local_admins = [local_administrators]

            device.last_seen = parse_date(device_raw.get('last_seen'))
            device.hostname = device_raw.get('name')
            device.total_number_of_cores = self._parse_int(device_raw.get('number_of_cores'))
            device.total_number_of_physical_processors = self._parse_int(device_raw.get('number_of_cpus'))

            os_string = f'{device_raw.get("os_version_and_architecture") or ""} ' \
                        f'{device_raw.get("os_architecture") or ""} {device_raw.get("os_build") or ""}'
            device.figure_os(os_string=os_string)

            total_ram = self._parse_int(device_raw.get('total_ram'))  # Bytes
            if total_ram and total_ram != 0:
                device.total_physical_memory = (total_ram / 1024 / 1024 / 1024)

            self._fill_next_think_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with parsing NextThink Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching NextThink Device for {device_raw}')

    def _fill_next_think_user_fields(self, user_raw: dict, user: MyUserAdapter):
        try:
            user.distinguished_name = user_raw.get('distinguished_name')
            user.first_seen = parse_date(user_raw.get('first_seen'))
            user.number_of_days_since_last_seen = self._parse_int(user_raw.get('number_of_days_since_last_seen'))
            user.full_name = user_raw.get('full_name')
            user.seen_on_mac = self._parse_bool(user_raw.get('seen_on_mac'))
            user.seen_on_mobile = self._parse_bool(user_raw.get('seen_on_mobile'))
            user.seen_on_windows = self._parse_bool(user_raw.get('seen_on_windows'))
            user.total_active_days = self._parse_int(user_raw.get('total_active_days'))
            user.user_uid = user_raw.get('user_uid ')

            try:
                user_type = user_raw.get('user_type')
                user.user_type = user_type
            except Exception:
                logger.debug(f'Received invalid user type {user_type}')

        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('name') or '')

            user.username = user_raw.get('name')
            user.user_sid = user_raw.get('sid')
            user.user_title = user_raw.get('job_title')
            user.user_department = user_raw.get('department')
            user.last_seen = parse_date(user_raw.get('last_seen'))
            user.display_name = user_raw.get('full_name')

            self._fill_next_think_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with parsing NextThink User for {user_raw}')
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
                logger.exception(f'Problem with fetching NextThink User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]
