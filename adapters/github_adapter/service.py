import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from github_adapter.client_id import get_client_id
from github_adapter.connection import GithubConnection

logger = logging.getLogger(f'axonius.{__name__}')


# class RepoPermissions(SmartJsonClass):
#     admin = Field(bool, 'Admin permission')
#     push = Field(bool, 'Push permission')
#     pull = Field(bool, 'Pull permission')


class UserRepo(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')
    full_name = Field(str, 'Full name')
    private = Field(bool, 'Private')
    html_url = Field(str, 'URL')
    description = Field(str, 'Description')
    fork = Field(bool, 'Fork')
    created = Field(datetime.datetime, 'Created')
    updated = Field(datetime.datetime, 'Updated')
    pushed = Field(datetime.datetime, 'Pushed at')
    git_url = Field(str, 'Git URL')
    owner = Field(str, 'Owner username')
    # perms = Field(RepoPermissions, 'Permissions',
    #               description='Organization owner permissions on this repository')


class GithubAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        gh_id = Field(int, 'GitHub user ID')
        node_id = Field(str, 'Node ID')
        url = Field(str, 'User URL')
        user_type = Field(str, 'Type')
        site_admin = Field(bool, 'Site admin')
        blog_url = Field(str, 'Blog')
        pub_repos = Field(int, 'Public repositories')
        pub_gists = Field(int, 'Public gists')
        bio = Field(str, 'Bio')
        mfa_enabled = Field(bool, '2FA enabled')
        repos = ListField(UserRepo,  'Repositories')
        org_2fa_req = Field(bool, 'Organization-level 2fa requirement enabled')
        def_repo_settings = Field(str, 'Organization-level default repository settings')

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
        connection = GithubConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
                                      token=client_config['auth_token'],
                                      org=client_config['org'])
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

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_users()

    @staticmethod
    def _clients_schema():
        """
        The schema GithubAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'GitHub Domain',
                    'type': 'string',
                    'default': 'https://api.github.com'
                },
                {
                    'name': 'org',
                    'title': 'Organization',
                    'type': 'string'
                },
                {
                    'name': 'auth_token',
                    'title': 'Authorization Token',
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
                'auth_token',
                'org',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_user(self, user_raw):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None

            # Axonius generic stuff
            user.id = str(user_id) + '_' + (user_raw.get('login') or '')
            user.username = user_raw.get('login')

            user.display_name = user_raw.get('name')
            user.mail = user_raw.get('email')
            user.image = user_raw.get('avatar_url')
            user.user_created = parse_date(user_raw.get('created_at'))

            # github-specific stuff
            user.gh_id = user_raw.get('id')
            user.node_id = user_raw.get('node_id')
            user.url = user_raw.get('html_url')
            user.user_type = user_raw.get('type')
            user.site_admin = user_raw.get('site_admin')
            user.blog_url = user_raw.get('blog')
            user.bio = user_raw.get('bio')
            user.pub_repos = user_raw.get('public_repos')
            user.pub_gists = user_raw.get('public_gists')
            user.mfa_enabled = user_raw.get('two_factor_authentication')
            # add org-user stuff if this is an org-user
            if user_raw.get('type') == 'Organization':
                user.org_2fa_req = user_raw.get('two_factor_requirement_enabled')
                user.def_repo_settings = user_raw.get('default_repository_settings')
            # add repositories
            repos = user_raw.get('x_repositories')
            if repos and isinstance(repos, list):
                for repo in repos:
                    if not isinstance(repo, dict):
                        continue
                    if isinstance(repo.get('owner'), dict):
                        owner = repo.get('owner').get('login')
                    else:
                        owner = None
                    # perms_dict = repo.get('permissions')
                    # if perms_dict and isinstance(perms_dict, dict):
                    #     perms = RepoPermissions(
                    #         admin=perms_dict.get('admin'),
                    #         push=perms_dict.get('push'),
                    #         pull=perms_dict.get('pull')
                    #     )
                    # else:
                    #     perms = None
                    user.repos.append(
                        UserRepo(
                            id=repo.get('id'),
                            name=repo.get('name'),
                            full_name=repo.get('full_name'),
                            private=repo.get('private'),
                            html_url=repo.get('html_url'),
                            description=repo.get('description'),
                            fork=repo.get('fork'),
                            created=parse_date(repo.get('created_at')),
                            updated=parse_date(repo.get('updated_at')),
                            pushed=parse_date(repo.get('pushed_at')),
                            git_url=repo.get('git_url'),
                            owner=owner,
                            # perms=perms
                        )
                    )
                # Readability...
            # Counts.
            user.set_raw(user_raw)
            return user
        except Exception as e:
            logger.exception(f'Error was: {str(e)} Problem with fetching GitHub user for {user_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        for user_raw in users_raw_data:
            user = self._create_user(user_raw)
            if user:
                yield user

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement, AdapterProperty.Assets]
