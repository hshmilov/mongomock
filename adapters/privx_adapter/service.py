import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none, parse_bool_from_raw
from privx_adapter.client_id import get_client_id
from privx_adapter.connection import PrivxConnection
from privx_adapter.structures import (Principal, PrivxDeviceInstance,
                                      PrivxSupportedService,
                                      PrivxUserInstance, Role)

logger = logging.getLogger(f'axonius.{__name__}')


class PrivxAdapter(AdapterBase):

    class MyDeviceAdapter(PrivxDeviceInstance):
        pass

    class MyUserAdapter(PrivxUserInstance):
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
        connection = PrivxConnection(
            oauth_client_id=client_config.get('oauth_client_id'),
            oauth_client_secret=client_config.get('oauth_client_secret'),
            domain=client_config.get('domain'),
            verify_ssl=client_config.get('verify_ssl'),
            https_proxy=client_config.get('https_proxy'),
            username=client_config.get('api_client_id'),
            password=client_config.get('api_client_secret')
        )
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as exception:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(exception))
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
        The schema PrivxAdapter expects from configs

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
                    'name': 'oauth_client_id',
                    'title': 'OAuth Client ID',
                    'type': 'string'
                },
                {
                    'name': 'oauth_client_secret',
                    'title': 'OAuth Client Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'api_client_id',
                    'title': 'API Client ID',
                    'type': 'string'
                },
                {
                    'name': 'api_client_secret',
                    'title': 'API Client Secret',
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
                'api_client_id',
                'api_client_secret',
                'oauth_client_id',
                'oauth_client_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_privx_device_fields(device_raw: dict, device: PrivxDeviceInstance):
        try:
            device.cloud_provider_region = device_raw.get('cloud_provider_region')
            device.audit_enabled = parse_bool_from_raw(device_raw.get('audit_enabled'))
            device.contact_address = device_raw.get('contact_address')
            device.deployable = parse_bool_from_raw(device_raw.get('deployable'))
            device.distinguished_name = device_raw.get('distinguished_name')
            device.external_id = device_raw.get('external_id')
            device.host_classification = device_raw.get('host_classification')
            device.host_type = device_raw.get('host_type')
            device.instance_id = device_raw.get('instance_id')
            device.organization = device_raw.get('organization')
            device.privx_configured = device_raw.get('privx_configured')
            device.source_id = device_raw.get('source_id')
            device.tofu = parse_bool_from_raw(device_raw.get('tofu'))
            device.updated_by = device_raw.get('updated_by')
            device.zone = device_raw.get('zone')

            principals = device_raw.get('principals')
            services = device_raw.get('services')

            if isinstance(services, list):
                device.supported_services = PrivxAdapter._parse_services_field(services)
            else:
                logger.warning(f'Unexpected type of services field, Raw Device: {str(device_raw)}')

            if isinstance(principals, list):
                device.principals = PrivxAdapter._parse_principals_field(principals)
            else:
                logger.warning(f'Unexpected type of principals field, Raw Device: {str(device_raw)}')

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: PrivxDeviceInstance):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('common_name') or '')
            device.hostname = device_raw.get('common_name')
            device.description = device_raw.get('comment')
            device.cloud_provider = device_raw.get('cloud_provider')
            device.first_seen = parse_date(device_raw.get('created'))
            device.last_seen = parse_date(device_raw.get('updated'))

            organizational_unit = device_raw.get('organizational_unit')
            addresses = device_raw.get('addresses')

            if isinstance(addresses, list):
                try:
                    device.add_ips_and_macs(ips=addresses)
                except Exception as e:
                    logger.warning(f'Failed to add ips information for device {device_raw}: {str(e)}')

            if organizational_unit and isinstance(organizational_unit, str):
                device.organizational_unit = [organizational_unit]

            self._fill_privx_device_fields(device_raw, device)
            device.set_raw(device_raw)

            return device

        except Exception as exception:
            logger.exception(f'Problem with fetching PrivX Device for {device_raw}, '
                             f'Exception: {exception}')
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
                device_raw = PrivxAdapter._remove_sensitive_fields(device_raw)
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Privx Device for {device_raw}')

    @staticmethod
    def _fill_privx_user_fields(user_raw: dict, user: PrivxUserInstance):
        user.password_change_required = parse_bool_from_raw(user_raw.get('password_change_required'))
        user.user_update_time = parse_date(user_raw.get('updated'))
        user.windows_account = user_raw.get('windows_account')
        user.unix_account = user_raw.get('unix_account')

    def _create_user(self, user_raw: dict, user: PrivxUserInstance):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = user_id + '_' + (user_raw.get('email') or '')
            user.username = user_raw.get('username')
            user.display_name = user_raw.get('display_name')
            user.mail = user_raw.get('email')
            user.user_created = parse_date(user_raw.get('created'))
            self._fill_privx_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Privx User for {user_raw}')
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
                logger.exception(f'Problem with fetching Privx User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]

    @staticmethod
    def _parse_principals_field(raw_principals: list):
        principals = []

        try:
            if not isinstance(raw_principals, list):
                logger.warning(f'Unexpected type of raw principals: {str(raw_principals)}')
                return principals

            for raw_principal in raw_principals:
                if not isinstance(raw_principal, dict):
                    logger.warning(f'Unexpected type of raw principal: {str(raw_principal)}')
                    continue

                roles = []
                raw_roles = raw_principal.get('roles')

                if not isinstance(raw_roles, list):
                    logger.warning(f'Unexpected type of raw roles: {str(raw_roles)}')
                    continue

                for raw_role in raw_roles:
                    if not isinstance(raw_role, dict):
                        logger.warning(f'Unexpected type of raw role: {str(raw_role)}')
                        continue

                    role = Role(
                        id=raw_role.get('id'),
                        name=raw_role.get('name')
                    )
                    roles.append(role)

                principal = Principal(
                    name=raw_principal.get('principal'),
                    source=raw_principal.get('source'),
                    use_user_account=parse_bool_from_raw(raw_principal.get('use_user_account')),
                    roles=roles
                )
                principals.append(principal)
        except Exception as ex:
            logger.warning(f'Error occurred while parsing principals, Error:{str(ex)} , '
                           f'Raw Principals:{str(raw_principals)}')

        return principals

    @staticmethod
    def _parse_services_field(raw_services: list):
        services = []
        try:
            if not isinstance(raw_services, list):
                logger.warning(f'Unexpected type of raw services: {str(raw_services)}')
                return services

            for raw_service in raw_services:
                if not isinstance(raw_service, dict):
                    logger.warning(f'Unexpected type of raw service: {str(raw_service)}')
                    continue

                service = PrivxSupportedService(
                    service_name=raw_service.get('service'),
                    address=raw_service.get('address'),
                    auth_type=raw_service.get('auth_type'),
                    login_page_url=raw_service.get('login_page_url'),
                    login_request_password_property=raw_service.get('login_request_password_property'),
                    login_request_url=raw_service.get('login_request_url'),
                    password_field_name=raw_service.get('password_field_name'),
                    port=int_or_none(raw_service.get('port')),
                    source=raw_service.get('source'),
                    status=raw_service.get('status'),
                    status_updated=raw_service.get('status_updated'),
                    username_field_name=raw_service.get('username_field_name')
                )
                services.append(service)
        except Exception as ex:
            logger.warning(f'Error occurred while parsing services, Error:{str(ex)} , '
                           f'Raw Services:{str(raw_services)}')
        return services

    @staticmethod
    def _remove_sensitive_fields(raw_device: dict):
        # Remove "passphrase" field
        if isinstance(raw_device, dict):
            principals = raw_device.get('principals')
            if isinstance(principals, list):
                for principal in principals:
                    if isinstance(principal, dict):
                        try:
                            principal.pop('passphrase')
                        except Exception:
                            pass

        return raw_device
