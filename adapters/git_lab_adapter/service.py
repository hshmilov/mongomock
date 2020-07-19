import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from git_lab_adapter.connection import GitLabConnection
from git_lab_adapter.client_id import get_client_id
from git_lab_adapter.consts import EXTRA_GROUPS, EXTRA_PROJECTS
from git_lab_adapter.structures import GitLabUserInstance, Project, Group

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class GitLabAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(GitLabUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, (bool, int)):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ('true', 'yes')
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
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = GitLabConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
                                      token=client_config['token'])
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
        The schema GitLabAdapter expects from configs

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
                    'title': 'API Token',
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
                'token',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _fill_git_lab_user_fields(self, user_raw: dict, user: MyUserAdapter):
        try:
            user.web_url = user_raw.get('web_url')
            user.location = user_raw.get('location')
            user.skype = user_raw.get('skype')
            user.linkedin = user_raw.get('linkedin')
            user.twitter = user_raw.get('twitter')
            user.note = user_raw.get('note')
            user.is_private = self._parse_bool(user_raw.get('private_profile'))
            user.current_ip = user_raw.get('current_sign_in_ip')
            user.current_ip_raw = user_raw.get('current_sign_in_ip')
            user.last_ip = user_raw.get('last_sign_in_ip')
            user.last_ip_raw = user_raw.get('last_sign_in_ip')

            if isinstance(user_raw.get(EXTRA_PROJECTS), list):
                projects = []
                for project_id, name in user_raw.get(EXTRA_PROJECTS):
                    project = Project()
                    project.id = self._parse_int(project_id)
                    project.name = name
                    projects.append(project)
                user.projects = projects

            if isinstance(user_raw.get(EXTRA_GROUPS), list):
                groups = []
                user_group_names = []
                for group_id, name in user_raw.get(EXTRA_GROUPS):
                    group = Group()
                    group.id = self._parse_int(group_id)
                    group.name = name
                    user_group_names.append(name)
                    groups.append(group)
                user.user_groups = groups
                user.groups = user_group_names

        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('name') or '')

            user.username = user_raw.get('username')
            user.mail = user_raw.get('email') or user_raw.get('public_email')
            user.display_name = user_raw.get('name')
            user.user_status = user_raw.get('state')
            user.user_created = parse_date(user_raw.get('created_at'))
            user.is_admin = self._parse_bool(user_raw.get('is_admin'))
            user.description = user_raw.get('bio')
            user.user_title = user_raw.get('job_title')
            user.user_country = user_raw.get('location')

            organization = user_raw.get('organization') or []
            if isinstance(organization, str):
                organization = [organization]

            user.organizational_unit = organization
            user.last_seen = parse_date(user_raw.get('last_sign_in_at'))

            self._fill_git_lab_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching GitLab User for {user_raw}')
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
                logger.exception(f'Problem with fetching GitLab User for {user_raw}')

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
            'pretty_name': 'GitLab Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'async_chunks': 50
        }

    def _on_config_update(self, config):
        self.__async_chunks = config.get('async_chunks') or 50
