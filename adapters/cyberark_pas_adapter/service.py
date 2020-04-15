import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from cyberark_pas_adapter.connection import CyberarkPasConnection
from cyberark_pas_adapter.client_id import get_client_id
from cyberark_pas_adapter.structures import CyberarkPasUserInstance, BusinessAddress, \
    Internet, Phones, PersonDetails

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class CyberarkPasAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(CyberarkPasUserInstance):
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
        connection = CyberarkPasConnection(domain=client_config['domain'],
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
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific domain

        :param client_name: The name of the client
        :param client_data: The data of the client.

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema CyberarkPasAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Domain',
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

    @staticmethod
    def _fill_user_business_address(user_raw: dict, user: MyUserAdapter):
        try:
            business_address = BusinessAddress()

            business_address.work_city = user_raw.get('workCity')
            business_address.work_country = user_raw.get('workCountry')
            business_address.work_state = user_raw.get('workState')
            business_address.work_street = user_raw.get('workStreet')
            business_address.work_zip = user_raw.get('workZip')

            user.business_address = business_address
        except Exception:
            logger.exception(f'Failed creating business address for user {user_raw}')

    @staticmethod
    def _fill_user_internet(user_raw: dict, user: MyUserAdapter):
        try:
            internet = Internet()

            internet.home_email = user_raw.get('homeEmail')
            internet.home_page = user_raw.get('homePage')
            internet.other_email = user_raw.get('otherEmail')

            user.internet = internet
        except Exception:
            logger.exception(f'Failed creating internet for user {user_raw}')

    @staticmethod
    def _fill_user_phones(user_raw: dict, user: MyUserAdapter):
        try:
            phone = Phones()

            phone.business = user.get('businessNumber')
            phone.fax = user.get('faxNumber')
            phone.home = user.get('homeNumber')
            phone.page = user.get('pagerNumber')

            user.phones = phone
        except Exception:
            logger.exception(f'Failed creating phones for user {user_raw}')

    @staticmethod
    def _fill_user_personal_details(user_raw: dict, user: MyUserAdapter):
        try:
            personal_details = PersonDetails()

            personal_details.street = user_raw.get('street')
            personal_details.state = user_raw.get('state')
            personal_details.zip = user_raw.get('zip')
            personal_details.organization = user_raw.get('organization')
            personal_details.profession = user_raw.get('profession')
            personal_details.middleName = user_raw.get('middleName')

            user.personal_details = personal_details
        except Exception:
            logger.exception(f'Failed creating personal details for user {user_raw}')

    @staticmethod
    def _fill_cyberark_pas_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            user.source = user_raw.get('source')
            user.change_password_next_login = user_raw.get('changePassOnNextLogon')
            user.user_type = user_raw.get('userType')
            user.location = user_raw.get('location')
            user.suspended = user_raw.get('suspended')

            # Specific type is not clear from documentation, support both str and list
            authentication_methods = user_raw.get('authenticationMethod') or []
            if isinstance(authentication_methods, str):
                authentication_methods = [authentication_methods]
            if not isinstance(authentication_methods, list):
                logger.exception(f'Invalid methods found: {authentication_methods}')
            else:
                user.authentication_methods = authentication_methods

            if user_raw.get('vaultAuthorization') and isinstance(user_raw.get('vaultAuthorization'), list):
                user.vault_authorization = user_raw.get('vaultAuthorization')

            if user_raw.get('unAuthorizedInterfaces') and isinstance(user_raw.get('unAuthorizedInterfaces'), list):
                user.unauthorized_interfaces = user_raw.get('unAuthorizedInterfaces')

            if user_raw.get('internet') and isinstance(user_raw.get('internet'), dict):
                user.mail = user_raw.get('internet').get('businessEmail')
                CyberarkPasAdapter._fill_user_internet(user_raw.get('internet'), user)

            if user_raw.get('phones') and isinstance(user_raw.get('phones'), dict):
                user.user_telephone_number = user_raw.get('phones').get('cellularNumber')
                CyberarkPasAdapter._fill_user_phones(user_raw.get('phones'), user)

            if user_raw.get('personalDetails') and isinstance(user_raw.get('personalDetails'), dict):
                user.user_title = user_raw.get('personalDetails').get('title')
                user.user_department = user_raw.get('personalDetails').get('department')
                user.user_city = user_raw.get('personalDetails').get('city')
                user.user_country = user_raw.get('personalDetails').get('country')
                user.first_name = user_raw.get('personalDetails').get('firstName')
                user.last_name = user_raw.get('personalDetails').get('lastName')
                CyberarkPasAdapter._fill_user_personal_details(user_raw.get('personalDetails'), user)

            if user_raw.get('businessAddress') and isinstance(user_raw.get('businessAddress'), dict):
                CyberarkPasAdapter._fill_user_business_address(user_raw.get('businessAddress'), user)

        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if not user_id:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = user_id

            user.username = user_raw.get('username')
            user.description = user_raw.get('description')
            user.last_logon = parse_date(user_raw.get('lastSuccessfulLoginDate'))
            user.password_never_expires = user_raw.get('passwordNeverExpires')
            user.account_expires = user_raw.get('expiryDate')
            user.account_disabled = user_raw.get('enableUser')

            self._fill_cyberark_pas_user_fields(user_raw, user)

            return user
        except Exception:
            logger.exception(f'Problem with fetching CyberArk PAS User for {user_raw}')
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
                user = self._create_user(user_raw, self._new_user_adapter())
                if user:
                    yield user
            except Exception:
                logger.exception(f'Problem with fetching CyberArk PAS User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
