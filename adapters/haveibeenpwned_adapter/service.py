import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.users.user_adapter import UserAdapter
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.smart_json_class import SmartJsonClass
from axonius.clients.haveibeenpwned.connection import HaveibeenpwnedConnection
from axonius.clients.haveibeenpwned.consts import HAVEIBEENPWNED_DOMAIN
from haveibeenpwned_adapter.client_id import get_client_id
from haveibeenpwned_adapter.execution import HaveibeenpwnedExecutionMixIn

logger = logging.getLogger(f'axonius.{__name__}')


class BreachData(SmartJsonClass):
    name = Field(str, 'Name')
    title = Field(str, 'Title')
    domain = Field(str, 'Domain')
    breach_date = Field(datetime.datetime, 'Breach Date')
    added_date = Field(datetime.datetime, 'Added Date')
    modified_date = Field(datetime.datetime, 'Modified Date')
    pwn_count = Field(int, 'Pwn Count')
    description = Field(str, 'Description')
    logo_path = Field(str, 'Logo Path')
    data_classes = ListField(str, 'Data Classes')
    is_verified = Field(bool, 'Is Verified')
    is_fabricated = Field(bool, 'Is Fabricated')
    is_sensitive = Field(bool, 'Is Sensitive')
    is_retired = Field(bool, 'Is Retired')
    is_spam_list = Field(bool, 'Is Spam List')


class HaveibeenpwnedAdapter(HaveibeenpwnedExecutionMixIn, AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        breaches_data = ListField(BreachData, 'Breaches Data')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(HAVEIBEENPWNED_DOMAIN)

    @staticmethod
    def get_connection(client_config):
        connection = HaveibeenpwnedConnection(verify_ssl=client_config['verify_ssl'],
                                              https_proxy=client_config.get('https_proxy'))
        return connection

    def _connect_client(self, client_config):
        try:
            connection = self.get_connection(client_config)
            with connection:
                connection.get_breach_account_info(client_config['email'])
            return connection, client_config['email']
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_users_by_client(key, data):
        connection, email = data
        with connection:
            return connection.get_breach_account_info(email), email

    @staticmethod
    def _clients_schema():
        """
        The schema HaveibeenpwnedAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'email',
                    'title': 'Account Email',
                    'type': 'string'
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
                'email',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_user(self, user_data, email):
        try:
            user = self._new_user_adapter()
            user.id = email
            user.mail = email
            for breach_data in user_data:
                try:
                    pwn_count = None
                    if isinstance(breach_data.get('PwnCount'), int):
                        pwn_count = breach_data.get('PwnCount')
                    data_classes = None
                    if isinstance(breach_data.get('DataClasses'), list):
                        data_classes = breach_data.get('DataClasses')
                    breach_data = BreachData(name=breach_data.get('Name'),
                                             title=breach_data.get('Title'),
                                             domain=breach_data.get('Domain'),
                                             breach_date=parse_date(breach_data.get('BreachDate')),
                                             added_date=parse_date(breach_data.get('AddedDate')),
                                             modified_date=parse_date(breach_data.get('ModifiedDate')),
                                             pwn_count=pwn_count,
                                             description=breach_data.get('Description'),
                                             logo_path=breach_data.get('LogoPath'),
                                             data_classes=data_classes,
                                             is_verified=bool(breach_data.get('IsVerified')),
                                             is_fabricated=bool(breach_data.get('IsFabricated')),
                                             is_sensitive=bool(breach_data.get('IsSensitive')),
                                             is_retired=bool(breach_data.get('IsRetired')),
                                             is_spam_list=bool(breach_data.get('IsSpamList'))
                                             )
                    user.breaches_data.append(breach_data)
                except Exception:
                    logger.exception(f'Problem with breach data {breach_data}')
            user.set_raw({'data': user_data})
            return user
        except Exception:
            logger.exception(f'Problem with fetching Haveibeenpwned')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, raw_data):
        user_data, email = raw_data
        user = self._create_user(user_data, email)
        if user:
            yield user

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
