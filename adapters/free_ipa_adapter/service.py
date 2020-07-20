import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from free_ipa_adapter.connection import FreeIpaConnection
from free_ipa_adapter.client_id import get_client_id
from free_ipa_adapter.structures import FreeIpaDeviceInstance, FreeIpaUserInstance

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class FreeIpaAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(FreeIpaDeviceInstance):
        pass

    class MyUserAdapter(FreeIpaUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _parse_list_to_str(value):
        if isinstance(value, list):
            try:
                return ', '.join(value)
            except Exception:
                return None
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
        connection = FreeIpaConnection(domain=client_config['domain'],
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
        The schema FreeIpaAdapter expects from configs

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
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _fill_free_ipa_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.user_class = self._parse_list_to_str(device_raw.get('userclass'))
            device.member_roles = device_raw.get('memberof_role')
            device.member_host_groups = device_raw.get('memberof_hostgroup')
            device.managed_by_host = device_raw.get('managedby_host')
            device.managing_host = device_raw.get('managing_host')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = self._parse_list_to_str(device_raw.get('ipauniqueid'))
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (self._parse_list_to_str(device_raw.get('cn')) or '')

            device.name = self._parse_list_to_str(device_raw.get('cn'))
            device.hostname = self._parse_list_to_str(device_raw.get('fqdn'))
            device.description = self._parse_list_to_str(device_raw.get('description'))
            device.physical_location = self._parse_list_to_str(device_raw.get('l'))

            os_string = f'{self._parse_list_to_str(device_raw.get("nsosversion")) or ""} ' \
                        f'{self._parse_list_to_str(device_raw.get("nshardwareplatform")) or ""}'
            device.figure_os(os_string=os_string)

            device.add_ips_and_macs(macs=device_raw.get('macaddress'))

            self._fill_free_ipa_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching FreeIpa Device for {device_raw}')
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
                logger.exception(f'Problem with fetching FreeIpa Device for {device_raw}')

    def _fill_free_ipa_user_fields(self, user_raw: dict, user: MyUserAdapter):
        try:
            user.user_class = self._parse_list_to_str(user_raw.get('userclass'))
            user.fax_number = user_raw.get('facsimiletelephonenumber')
            user.telephone_numbers = user_raw.get('telephonenumber')
            user.mobile_numbers = user_raw.get('mobile')
            user.preferred_language = self._parse_list_to_str(user_raw.get('preferredlanguage'))
            user.postal_code = self._parse_list_to_str(user_raw.get('postalcode'))
            user.state = self._parse_list_to_str(user_raw.get('st'))
            user.street = self._parse_list_to_str(user_raw.get('street'))
            user.mails = user_raw.get('mail')
            user.member_roles = user_raw.get('memberof_rule')

        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = self._parse_list_to_str(user_raw.get('ipauniqueid'))
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = user_id + '_' + (self._parse_list_to_str(user_raw.get('displayname')) or '')

            user.display_name = self._parse_list_to_str(user_raw.get('displayname'))
            user.first_name = self._parse_list_to_str(user_raw.get('givenname'))
            user.last_name = self._parse_list_to_str(user_raw.get('sn'))
            user.employee_number = self._parse_list_to_str(user_raw.get('employeenumber'))
            user.employee_type = self._parse_list_to_str(user_raw.get('employeetype'))
            user.user_city = self._parse_list_to_str(user_raw.get('l'))
            user.organizational_unit = user_raw.get('ou')
            user.groups = user_raw.get('memberof_group')
            user.user_title = self._parse_list_to_str(user_raw.get('title'))

            self._fill_free_ipa_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching FreeIpa User for {user_raw}')
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
                logger.exception(f'Problem with fetching FreeIpa User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]
