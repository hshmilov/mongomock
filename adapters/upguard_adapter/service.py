import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from upguard_adapter.connection import UpguardConnection
from upguard_adapter.client_id import get_client_id
from upguard_adapter.structures import UpguardUserInstance, BreachData

logger = logging.getLogger(f'axonius.{__name__}')


class UpguardAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UpguardUserInstance):
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
        connection = UpguardConnection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       apikey=client_config['apikey'])
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
        Get all users from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            return client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema UpguardAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'UpGuard Domain',
                    'type': 'string',
                    'default': 'https://cyber-risk.upguard.com'
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

    @staticmethod
    def _fill_upguard_user_fields(user_raw: dict, user: MyUserAdapter, breaches_id_dict: dict):
        try:
            user.last_breach_date = parse_date(user_raw.get('last_breach_date'))
            user.num_breaches = user_raw.get('num_breaches') if isinstance(user_raw.get('num_breaches'), int) else None
            breach_ids = user_raw.get('breach_ids')
            if not isinstance(breach_ids, list):
                breach_ids = []
            for breach_id in breach_ids:
                try:
                    breach_data = breaches_id_dict.get(breach_id)
                    if not isinstance(breach_data, dict):
                        breach_data = {}
                    exposed_data_classes = breach_data.get('exposed_data_classes') if isinstance(
                        breach_data.get('exposed_data_classes'), list) else None
                    total_exposures = breach_data.get('total_exposures') if isinstance(
                        breach_data.get('total_exposures'), int) else None
                    breach_obj = BreachData(date_occurred=parse_date(breach_data.get('date_occurred')),
                                            description=breach_data.get('description'),
                                            domain=breach_data.get('domain'),
                                            exposed_data_classes=exposed_data_classes,
                                            name=breach_data.get('name'),
                                            title=breach_data.get('title'),
                                            total_exposures=total_exposures)
                    user.breaches_data.append(breach_obj)
                except Exception:
                    logger.exception(f'Problem with breach id {breach_id}')
        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter, breaches_id_dict: dict):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('name') or '')
            user.username = user_raw.get('name')
            user.domain = user_raw.get('domain')
            self._fill_upguard_user_fields(user_raw, user, breaches_id_dict)

            user.set_raw(user_raw)

            return user
        except Exception:
            logger.exception(f'Problem with fetching Upguard User for {user_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        """
        Gets raw data and yields User objects.
        :param users_raw_data: the raw data we get.
        :return:
        """
        breached_identities, breaches_id_dict = users_raw_data
        for user_raw in breached_identities:
            if not user_raw:
                continue
            try:
                # noinspection PyTypeChecker
                user = self._create_user(user_raw, self._new_user_adapter(), breaches_id_dict)
                if user:
                    yield user
            except Exception:
                logger.exception(f'Problem with fetching Upguard User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
