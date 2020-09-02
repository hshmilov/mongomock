import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw
from logmein_adapter.client_id import get_client_id
from logmein_adapter.connection import LogmeinConnection
from logmein_adapter.structures import LogmeinDeviceInstance, LogmeinUserInstance
from logmein_adapter.consts import EXTRA_DETAILS_NAME, PAREN_RE

logger = logging.getLogger(f'axonius.{__name__}')


class LogmeinAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(LogmeinDeviceInstance):
        pass

    class MyUserAdapter(LogmeinUserInstance):
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
        connection = LogmeinConnection(domain=client_config.get('domain'),
                                       company_id=client_config.get('company_id'),
                                       pre_shared_key=client_config.get('pre_shared_key'),
                                       verify_ssl=client_config.get('verify_ssl'),
                                       https_proxy=client_config.get('https_proxy'))
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
        The schema LogmeinAdapter expects from configs

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
                    'name': 'company_id',
                    'title': 'Company ID',
                    'type': 'string'
                },
                {
                    'name': 'pre_shared_key',
                    'title': 'Pre-Shared Key (PSK)',
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
                'company_id',
                'pre_shared_key',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _fill_logmein_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.is_host_online = parse_bool_from_raw(device_raw.get('isHostOnline'))

            hardware_details = self._get_extra_details('hardware', device_raw)
            hardware_info = hardware_details.get('hardwareInfo')
            if hardware_info and isinstance(hardware_info, dict):
                device.asset_tag = hardware_info.get('assetTag')

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    @staticmethod
    def _get_extra_details(name, device_raw):
        if device_raw.get(EXTRA_DETAILS_NAME.format(name=name)) and isinstance(
                device_raw.get(EXTRA_DETAILS_NAME.format(name=name)), dict):
            return device_raw.get(EXTRA_DETAILS_NAME.format(name=name))
        return {}

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('description') or '')
            hostname = self._get_extra_details('computer', device_raw).get('computerDescription')
            if (isinstance(hostname, str) and
                    (('(' in hostname) or (')' in hostname))):
                # remove parentheses from hostname
                try:
                    hostname = PAREN_RE.sub('', hostname).strip()
                except Exception:
                    logger.exception(f'Failed removing parenthases from hostname {hostname}')

            device.hostname = hostname
            device.description = device_raw.get('description')
            device.last_seen = parse_date(self._get_extra_details('computer', device_raw).get('lastOnline'))

            hardware_details = self._get_extra_details('hardware', device_raw)
            if hardware_details.get('networkConnections') and \
                    isinstance(hardware_details.get('networkConnections'), list):

                ips = [network.get('ipAddress') for network in hardware_details.get('networkConnections') if
                       isinstance(network, dict) and isinstance(network.get('ipAddress'), str)]
                macs = [network.get('macAddress') for network in hardware_details.get('networkConnections') if
                        isinstance(network, dict) and isinstance(network.get('macAddress'), str)]

                device.add_ips_and_macs(ips=ips, macs=macs)

            system_details = self._get_extra_details('system', device_raw)
            external_ip = system_details.get('externalIp')
            if isinstance(external_ip, str):
                device.add_public_ip(external_ip)
            elif isinstance(external_ip, list):
                for ip in external_ip:
                    if isinstance(ip, str):
                        device.add_public_ip(ip)

            operating_system = system_details.get('operatingSystem')
            if operating_system and isinstance(operating_system, dict):
                device.figure_os(operating_system.get('type'))
                device.os.install_date = parse_date(operating_system.get('installDate'))

            if device_raw.get('extra_avs') and isinstance(device_raw.get('extra_avs'), list):
                for av in device_raw.get('extra_avs'):
                    # extra_avs is in the format of List(Tuple).
                    device.add_installed_software(name=av[0],
                                                  version=av[1])

            self._fill_logmein_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Logmein Device for {device_raw}')
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
                logger.exception(f'Problem with fetching Logmein Device for {device_raw}')

    @staticmethod
    def _create_user(user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('firstName') or '')

            user.mail = user_raw.get('email')
            user.first_name = user_raw.get('firstName')
            user.last_name = user_raw.get('lastName')
            user.is_master_account_holder = parse_bool_from_raw(user_raw.get('is_master_account_holder'))
            user.last_seen = parse_date(user_raw.get('lastLoginDate'))

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Logmein User for {user_raw}')
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
                logger.exception(f'Problem with fetching Logmein User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]
