import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.bitbucket.connection import BitbucketConnection
from axonius.clients.bitbucket.consts import DEFAULT_MAX_COMMITS, MAXIMUM_FOR_MAX_COMMITS
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from bitbucket_adapter.client_id import get_client_id
from bitbucket_adapter.structures import BitbucketDeviceInstance, Project, Commit, User

logger = logging.getLogger(f'axonius.{__name__}')


class BitbucketAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(BitbucketDeviceInstance):
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
        connection = BitbucketConnection(domain=client_config.get('domain'),
                                         verify_ssl=client_config.get('verify_ssl'),
                                         https_proxy=client_config.get('https_proxy'),
                                         proxy_username=client_config.get('proxy_username'),
                                         proxy_password=client_config.get('proxy_password'),
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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(max_commits=self.__max_commits)

    @staticmethod
    def _clients_schema():
        """
        The schema BitbucketAdapter expects from configs

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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_bitbucket_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.state = device_raw.get('state')
            device.public = parse_bool_from_raw(device_raw.get('public'))
            device.status_message = device_raw.get('statusMessage')
            project_raw = device_raw.get('project')
            if isinstance(project_raw, dict):
                project = Project()
                project.project_id = int_or_none(project_raw.get('id'))
                project.key = project_raw.get('key')
                project.name = project_raw.get('name')
                project.public = parse_bool_from_raw(device_raw.get('public'))
                project.description = project_raw.get('description')
                project.project_type = project_raw.get('type')

            commits_raw = device_raw.get('extra_commits')
            device.commits = []
            if isinstance(commits_raw, list):
                for commit_raw in commits_raw:
                    commit = Commit()
                    commit.commit_id = commit_raw.get('id')
                    commit.display_id = commit_raw.get('displayId')
                    commit.message = commit_raw.get('message')
                    author_raw = commit_raw.get('author')
                    if isinstance(author_raw, dict):
                        author = User()
                        author.name = author_raw.get('name')
                        author.email = author_raw.get('emailAddress')
                        author.time = parse_date(commit_raw.get('authorTimestamp'))
                        commit.author = author

                    committer_raw = commit_raw.get('committer')
                    if isinstance(committer_raw, dict):
                        committer = User()
                        committer.name = committer_raw.get('name')
                        committer.email = committer_raw.get('emailAddress')
                        committer.time = parse_date(commit_raw.get('committerTimestamp'))
                        commit.committer = committer

                    device.commits.append(commit)

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
            device.description = device_raw.get('description')

            self._fill_bitbucket_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Bitbucket Device for {device_raw}')
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
                logger.exception(f'Problem with fetching Bitbucket Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        """
        Return the schema this class wants to have for the config
        """
        return {
            'items': [
                {
                    'name': 'max_commits',
                    'title': 'Fetch maximum commits',
                    'type': 'number',
                    'default': DEFAULT_MAX_COMMITS,
                    'max': MAXIMUM_FOR_MAX_COMMITS
                }
            ],
            'required': [],
            'pretty_name': 'Bitbucket Server Configuration',
            'type': 'array',
        }

    @classmethod
    def _db_config_default(cls):
        """
        Return the default configuration for this class
        """
        return {
            'max_commits': DEFAULT_MAX_COMMITS
        }

    def _on_config_update(self, config):
        """
        Virtual
        This is called on every inheritor when the config was updated.
        """
        self.__max_commits = int_or_none(config.get('max_commits')) or DEFAULT_MAX_COMMITS
        if self.__max_commits >= MAXIMUM_FOR_MAX_COMMITS:
            self.__max_commits = MAXIMUM_FOR_MAX_COMMITS
