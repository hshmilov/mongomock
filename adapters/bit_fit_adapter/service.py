import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.bit_fit.connection import BitFitConnection
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none
from bit_fit_adapter.client_id import get_client_id
from bit_fit_adapter.structures import BitFitDeviceInstance, BitFitUserInstance, AssetLocation, AssetType

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class BitFitAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(BitFitDeviceInstance):
        pass

    class MyUserAdapter(BitFitUserInstance):
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
        connection = BitFitConnection(domain=client_config.get('domain'),
                                      verify_ssl=client_config.get('verify_ssl'),
                                      https_proxy=client_config.get('https_proxy'),
                                      proxy_username=client_config.get('proxy_username'),
                                      proxy_password=client_config.get('proxy_password'),
                                      client_id=client_config.get('client_id'),
                                      client_secret=client_config.get('client_secret'),
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
        The schema BitFitAdapter expects from configs

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
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
                    'title': 'Client Secret',
                    'type': 'string',
                    'format': 'password'
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
                'domain',
                'client_id',
                'client_secret',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_bit_fit_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.shelf = int_or_none(device_raw.get('shelf'))
            device.size = int_or_none(device_raw.get('size'))
            device.side = device_raw.get('side')
            device.lease_info = device_raw.get('lease_info')
            device.lease_date = parse_date(device_raw.get('lease_date'))
            device.lease_expiration_date = parse_date(device_raw.get('lease_expiration_date'))
            device.vendor_ssd = device_raw.get('vendor_ssd_spec')
            device.vendor_ram = device_raw.get('vendor_ram_spec')
            device.depth = device_raw.get('depth')
            device.created_at = parse_date(device_raw.get('created_at'))
            device.updated_at = parse_date(device_raw.get('updated_at'))

            location_ids = []
            location_name = None
            location_raw = device_raw.get('location')
            if int_or_none(device_raw.get('location_id')):
                location_ids.append(int_or_none(device_raw.get('location_id')))
            if int_or_none(device_raw.get('location_id2')):
                location_ids.append(int_or_none(device_raw.get('location_id2')))
            if isinstance(location_raw, dict):
                if int_or_none(location_raw.get('id')):
                    location_ids.append(int_or_none(location_raw.get('id')))
                location_name = location_raw.get('name')
            asset_location = AssetLocation()
            asset_location.ids = location_ids
            asset_location.name = location_name
            device.asset_location = asset_location

            if isinstance(device_raw.get('type'), dict):
                type_raw = device_raw.get('type')
                asset_type = AssetType()
                asset_type.id = int_or_none(type_raw.get('id')) or int_or_none(device_raw.get('type_id'))
                asset_type.label = type_raw.get('label')
                device.asset_type = asset_type
            elif int_or_none(device_raw.get('type_id')):
                asset_type = AssetType()
                asset_type.id = int_or_none(device_raw.get('type_id'))
                device.asset_type = asset_type

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.name = device_raw.get('name')
            device.device_serial = device_raw.get('serial_number')
            device.description = device_raw.get('description')
            device.add_nic(mac=device_raw.get('mac_address'))

            config_raw = device_raw.get('config')
            if isinstance(config_raw, dict):
                device.device_model = config_raw.get('model')
            else:
                device.device_model = device_raw.get('model')

            self._fill_bit_fit_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching BitFit Device for {device_raw}')
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
                logger.exception(f'Problem with fetching BitFit Device for {device_raw}')

    @staticmethod
    def _create_user(user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('first_name') or '')

            user.first_name = user_raw.get('first_name')
            user.last_name = user_raw.get('last_name')
            user.username = user_raw.get('username')
            user.user_status = user_raw.get('status')
            user.display_name = user_raw.get('full_name') or f'{user_raw.get("first_name")} {user_raw.get("last_name")}'
            user.user_created = parse_date(user_raw.get('created_at'))
            user.user_title = user_raw.get('title')
            user.user_telephone_number = user_raw.get('phone')

            mail = user_raw.get('email')
            if isinstance(mail, str):
                user.mail = mail
                if '@' in mail:
                    user.domain = mail.split('@', 1)[1]

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching BitFit User for {user_raw}')
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
                logger.exception(f'Problem with fetching BitFit User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]
