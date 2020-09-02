import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none, parse_bool_from_raw
from axonius.utils.datetime import parse_date
from slack_adapter.connection import SlackConnection
from slack_adapter.client_id import get_client_id
from slack_adapter.structures import SlackUserInstance, Profile, EnterpriseGridUser

logger = logging.getLogger(f'axonius.{__name__}')


class SlackAdapter(AdapterBase, Configurable):
    class MyUserAdapter(SlackUserInstance):
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
        connection = SlackConnection(domain=client_config['domain'],
                                     token=client_config['token'],
                                     is_enterprise=client_config['is_enterprise'],
                                     verify_ssl=client_config['verify_ssl'],
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

    # pylint: disable=arguments-differ
    def _query_users_by_client(self, client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list(
                async_chunks=self.__async_chunks
            )

    @staticmethod
    def _clients_schema():
        """
        The schema SlackAdapter expects from configs

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
                    'name': 'token',
                    'title': 'Authentication Token',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'is_enterprise',
                    'title': 'Enterprise Grid Organization',
                    'type': 'bool'
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
                'token',
                'is_enterprise',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_user_profile(user_raw: dict, user: MyUserAdapter):
        try:
            profile = Profile()
            profile.display_name_normalized = user_raw.get('display_name_normalized')
            profile.real_name = user_raw.get('real_name')
            profile.real_name_normalized = user_raw.get('real_name_normalize')
            profile.skype = user_raw.get('skype')
            profile.team = user_raw.get('team')
            profile.status_emoji = user_raw.get('status_emoji')
            profile.status_text = user_raw.get('status_text')
            user.profile = profile
        except Exception:
            logger.exception(f'Failed creating profile for user {user_raw}')

    @staticmethod
    def _fill_user_enterprise_user(user_raw: dict, user: MyUserAdapter):
        try:
            enterprise_grid_user = EnterpriseGridUser()
            enterprise_grid_user.enterprise_id = user_raw.get('enterprise_id')
            enterprise_grid_user.enterprise_name = user_raw.get('enterprise_name')
            enterprise_grid_user.id = user_raw.get('id')
            enterprise_grid_user.is_admin = parse_bool_from_raw(user_raw.get('is_admin'))
            enterprise_grid_user.is_owner = parse_bool_from_raw(user_raw.get('is_owner'))
            if isinstance(user_raw.get('teams'), list):
                enterprise_grid_user.teams = user_raw.get('teams')
            elif isinstance(user_raw.get('teams'), str):
                enterprise_grid_user.teams = [user_raw.get('teams')]
            user.enterprise_user = enterprise_grid_user
        except Exception:
            logger.exception(f'Failed creating enterprise grid user for user {user_raw}')

    def _fill_slack_user_fields(self, user_raw: dict, user: MyUserAdapter):
        try:
            user.always_active = parse_bool_from_raw(user_raw.get('always_active'))
            try:
                billing_active = (user_raw.get('billable_info') or {}).get('billing_active')
                if isinstance(billing_active, bool):
                    user.billing_active = billing_active
            except Exception:
                logger.exception(f'Problem with billing')
            user.color = user_raw.get('color')
            user.deleted = parse_bool_from_raw(user_raw.get('deleted'))
            user.has_2fa = parse_bool_from_raw(user_raw.get('has_2fa'))
            user.is_app_user = parse_bool_from_raw(user_raw.get('is_app_user'))
            user.is_invited_user = parse_bool_from_raw(user_raw.get('is_invited_user'))
            user.is_owner = parse_bool_from_raw(user_raw.get('is_owner'))
            user.is_primary_owner = parse_bool_from_raw(user_raw.get('is_primary_owner'))
            user.is_restricted = parse_bool_from_raw(user_raw.get('is_restricted'))
            user.is_stranger = parse_bool_from_raw(user_raw.get('is_stranger'))
            user.is_ultra_restricted = parse_bool_from_raw(user_raw.get('is_ultra_restricted'))
            user.locale = user_raw.get('locale')
            user.two_factor_type = user_raw.get('two_factor_type')
            user.user_time_zone = user_raw.get('user_time_zone')
            user.user_time_zone_label = user_raw.get('user_time_zone_label')
            user.user_time_zone_offset = int_or_none(user_raw.get('user_time_zone_offset'))
            if isinstance(user_raw.get('team_id'), list):
                user.team_ids = user_raw.get('team_id')
            elif isinstance(user_raw.get('team_id'), str):
                user.team_ids = [user_raw.get('team_id')]
            if user_raw.get('profile') and isinstance(user_raw.get('profile'), dict):
                self._fill_user_profile(user_raw.get('profile'), user)

            if user_raw.get('enterprise_user') and isinstance(user_raw.get('enterprise_user'), dict):
                self._fill_user_enterprise_user(user_raw.get('enterprise_user'), user)

        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    @staticmethod
    def _get_image_attribute(profile: dict):
        user_image = profile.get('image_original') or profile.get('image_512') or profile.get('image_192') or \
            profile.get('image_72') or profile.get('image_48') or profile.get('image_32') or \
            profile.get('image_24')
        return user_image

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = user_id
            user.is_admin = parse_bool_from_raw(user_raw.get('is_admin'))
            # updated is 0 when the date doesn't exist
            if user_raw.get('updated') != 0:
                user.last_seen = parse_date(user_raw.get('updated'))
            profile = user_raw.get('profile')
            if profile and isinstance(profile, dict):
                user.display_name = profile.get('display_name')
                user.first_name = profile.get('first_name')
                user.last_name = profile.get('last_name')
                user.mail = profile.get('email')
                user.user_telephone_number = profile.get('phone')
                user.user_title = profile.get('title')
                user.image = self._get_image_attribute(profile)

                if profile.get('first_name') and profile.get('last_name'):
                    user.username = f'{profile.get("first_name")} {profile.get("last_name")}'
                elif profile.get('display_name'):
                    user.username = profile.get('display_name')
                elif profile.get('real_name'):
                    user.username = profile.get('real_name')
                else:
                    user.username = profile.get('first_name') or profile.get('last_name') or None

            self._fill_slack_user_fields(user_raw, user)
            user.set_raw(user_raw)
            return user
        except Exception as e:
            logger.exception(f'Problem with fetching Slack User for {user_raw}')
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
                logger.exception(f'Problem with fetching Slack User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'async_chunks',
                    'type': 'integer',
                    'title': 'Async chunks in parallel'
                }
            ],
            'required': [
                'async_chunks'
            ],
            'pretty_name': 'Slack Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'async_chunks': 50
        }

    def _on_config_update(self, config):
        self.__async_chunks = config.get('async_chunks') or 50
