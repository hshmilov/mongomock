import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.mixins.configurable import Configurable
from toriihq_adapter.connection import ToriihqConnection
from toriihq_adapter.client_id import get_client_id
from toriihq_adapter.consts import TORIIHQ_DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class ToriihqAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        lifecycle_status = Field(str, 'Lifecycle Status')
        role = Field(str, 'Role')
        is_external = Field(bool, 'Is External')

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
        connection = ToriihqConnection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       apikey=client_config['apikey'])
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
    def _clients_schema():
        """
        The schema ToriihqAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Torii Domain',
                    'type': 'string',
                    'default': TORIIHQ_DEFAULT_DOMAIN
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
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
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_users_by_client(key, data):
        with data:
            yield from data.get_user_list()

    def _create_user(self, user_raw):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('email') or '')
            user.first_name = user_raw.get('firstName')
            user.last_name = user_raw.get('lastName')
            user.mail = user_raw.get('email')
            user.role = user_raw.get('role')
            user.lifecycle_status = user_raw.get('lifecycleStatus')
            user.user_created = parse_date(user_raw.get('creationTime'))
            try:
                apps_raw = user_raw.get('apps_raw')
                if not isinstance(apps_raw, list):
                    apps_raw = []
                for app_raw in apps_raw:
                    try:
                        user.add_user_application(app_name=app_raw.get('name'),
                                                  app_state=app_raw.get('state'),
                                                  is_user_removed_from_app=app_raw.get('isUserRemovedFromApp')
                                                  if isinstance(app_raw.get('isUserRemovedFromApp'), bool) else None)
                    except Exception:
                        logger.exception(f'Problem getting app {app_raw}')
            except Exception:
                logger.exception(f'Problem getting apps for {user_raw}')
            is_external = user_raw.get('isExternal') if isinstance(user_raw.get('isExternal'), bool) else None
            if self.__exclude_external_users and is_external is True:
                return None
            user.is_external = is_external
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching BambooHR user for {user_raw}')
            return None

    def _parse_users_raw_data(self, users_raw_data):
        for user_raw in users_raw_data:
            user = self._create_user(user_raw)
            if user:
                yield user

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'exclude_external_users',
                    'title': 'Exclude External Users',
                    'type': 'bool'
                }
            ],
            'required': [
                'exclude_external_users'
            ],
            'pretty_name': 'Toriihq Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'exclude_external_users': False
        }

    def _on_config_update(self, config):
        self.__exclude_external_users = config['exclude_external_users']
