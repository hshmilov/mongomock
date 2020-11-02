import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import normalize_timezone_date, int_or_none
from git_lab_adapter.connection import GitLabConnection
from git_lab_adapter.client_id import get_client_id
from git_lab_adapter.consts import EXTRA_GROUPS, EXTRA_PROJECTS
from git_lab_adapter.structures import GitLabUserInstance, GitLabDeviceInstance, Project, Group, Statistics, \
    Namespace, VulnerabilityFinding, VulnerabilityIdentifier, Location, Dependency

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class GitLabAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(GitLabDeviceInstance):
        pass

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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(fetch_projects_as_devices=self.__fetch_projects_as_devices)

    # pylint: disable=too-many-statements, too-many-branches, too-many-nested-blocks
    def _fill_git_lab_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.default_branch = device_raw.get('default_branch')
            device.visibility = device_raw.get('visibility')
            device.ssh_url_to_repo = device_raw.get('ssh_url_to_repo')
            device.http_url_to_repo = device_raw.get('http_url_to_repo')
            device.web_url = device_raw.get('web_url')
            device.readme_url = device_raw.get('readme_url')
            device.tag_list = device_raw.get('tag_list')
            device.name_with_namespace = device_raw.get('name_with_namespace')
            device.path = device_raw.get('path')
            device.path_with_namespace = device_raw.get('path_with_namespace')
            device.issues_enabled = self._parse_bool(device_raw.get('issues_enabled'))
            device.open_issues_count = self._parse_bool(device_raw.get('open_issues_count'))
            device.merge_requests_enabled = self._parse_bool(device_raw.get('merge_requests_enabled'))
            device.jobs_enabled = self._parse_bool(device_raw.get('jobs_enabled'))
            device.wiki_enabled = self._parse_bool(device_raw.get('wiki_enabled'))
            device.snippets_enabled = self._parse_bool(device_raw.get('snippets_enabled'))
            device.can_create_merge_request_in = self._parse_bool(device_raw.get('can_create_merge_request_in'))
            device.resolve_outdated_diff_discussions = self._parse_bool(
                device_raw.get('resolve_outdated_diff_discussions'))
            device.container_registry_enabled = self._parse_bool(device_raw.get('container_registry_enabled'))
            device.creator_id = self._parse_int(device_raw.get('creator_id'))
            device.import_status = device_raw.get('import_status')
            device.archived = self._parse_bool(device_raw.get('archived'))
            device.avatar_url = device_raw.get('avatar_url')
            device.shared_runners_enabled = self._parse_bool(device_raw.get('shared_runners_enabled'))
            device.forks_count = self._parse_int(device_raw.get('forks_count'))
            device.star_count = self._parse_int(device_raw.get('star_count'))
            device.runners_token = device_raw.get('runners_token')
            device.ci_default_git_depth = self._parse_int(device_raw.get('ci_default_git_depth'))
            device.public_jobs = self._parse_bool(device_raw.get('public_jobs'))
            device.only_allow_merge_if_pipeline_succeeds = self._parse_bool(
                device_raw.get('only_allow_merge_if_pipeline_succeeds'))
            device.allow_merge_on_skipped_pipeline = self._parse_bool(device_raw.get('allow_merge_on_skipped_pipeline'))
            device.only_allow_merge_if_all_discussions_are_resolved = self._parse_bool(
                device_raw.get('only_allow_merge_if_all_discussions_are_resolved'))
            device.remove_source_branch_after_merge = self._parse_bool(
                device_raw.get('remove_source_branch_after_merge'))
            device.request_access_enabled = self._parse_bool(device_raw.get('request_access_enabled'))
            device.merge_method = device_raw.get('merge_method')
            device.autoclose_referenced_issues = self._parse_bool(device_raw.get('autoclose_referenced_issues'))
            device.suggestion_commit_message = device_raw.get('suggestion_commit_message')
            device.marked_for_deletion_on = parse_date(
                normalize_timezone_date(device_raw.get('marked_for_deletion_on')))
            device.approvals_before_merge = self._parse_int(device_raw.get('approvals_before_merge'))
            device.auto_cancel_pending_pipelines = self._parse_bool(device_raw.get('auto_cancel_pending_pipelines'))
            device.auto_devops_deploy_strategy = self._parse_bool(device_raw.get('auto_devops_deploy_strategy'))
            device.auto_devops_enabled = self._parse_bool(device_raw.get('auto_devops_enabled'))
            device.build_coverage_regex = device_raw.get('build_coverage_regex')
            device.build_timeout = self._parse_int(device_raw.get('build_timeout'))
            device.builds_access_level = device_raw.get('builds_access_level')
            device.ci_config_path = device_raw.get('ci_config_path')
            device.empty_repo = self._parse_bool(device_raw.get('empty_repo'))
            device.external_authorization_classification_label = device_raw.get(
                'external_authorization_classification_label')
            device.forking_access_level = device_raw.get('forking_access_level')
            device.service_desk_address = device_raw.get('service_desk_address')
            device.service_desk_enabled = self._parse_bool(device_raw.get('service_desk_enabled'))

            device.shared_with_groups = []
            if isinstance(device_raw.get('shared_with_groups'), list):
                for shared_group in device_raw.get('shared_with_groups'):
                    if not isinstance(shared_group, dict):
                        continue
                    group = Group()
                    group.id = shared_group.get('group_id')
                    group.name = shared_group.get('group_name')
                    device.shared_with_groups.append(group)

            if isinstance(device_raw.get('statistics'), dict):
                statistics = Statistics()
                statistics.commit_count = int_or_none(device_raw.get('statistics').get('commit_count'))
                statistics.storage_size = int_or_none(device_raw.get('statistics').get('storage_size'))
                statistics.wiki_size = int_or_none(device_raw.get('statistics').get('wiki_size'))
                statistics.repository_size = int_or_none(device_raw.get('statistics').get('repository_size'))
                statistics.lfs_objects_size = int_or_none(device_raw.get('statistics').get('lfs_objects_size'))
                statistics.job_artifacts_size = int_or_none(device_raw.get('statistics').get('job_artifacts_size'))
                statistics.packages_size = int_or_none(device_raw.get('statistics').get('packages_size'))
                statistics.snippets_size = int_or_none(device_raw.get('statistics').get('snippets_size'))
                device.statistics = statistics

            if isinstance(device_raw.get('namespace'), dict):
                namespace = Namespace()
                namespace.id = int_or_none(device_raw.get('namespace').get('id'))
                namespace.name = device_raw.get('namespace').get('name')
                namespace.path = device_raw.get('namespace').get('path')
                namespace.kind = device_raw.get('namespace').get('kind')
                namespace.full_path = device_raw.get('namespace').get('full_path')
                device.namespace = namespace

            if isinstance(device_raw.get('extra_vulnerability_findings'), list):
                vulnerability_findings = []
                for vulnerability_finding_raw in device_raw.get('extra_vulnerability_findings'):
                    if not isinstance(vulnerability_finding_raw, dict):
                        continue
                    vulnerability_finding = VulnerabilityFinding()
                    vulnerability_finding.name = vulnerability_finding_raw.get('name')
                    vulnerability_finding.id = int_or_none(vulnerability_finding_raw.get('id'))
                    vulnerability_finding.description = vulnerability_finding_raw.get('description')
                    vulnerability_finding.confidence = vulnerability_finding_raw.get('confidence')
                    vulnerability_finding.severity = vulnerability_finding_raw.get('severity')
                    vulnerability_finding.solution = vulnerability_finding_raw.get('solution')

                    if isinstance(vulnerability_finding_raw.get('location'), dict):
                        location_raw = vulnerability_finding_raw.get('location')
                        location = Location()
                        location.file = location_raw.get('file')

                        if isinstance(location_raw.get('dependency'), dict):
                            dependency_raw = location_raw.get('dependency')
                            dependency = Dependency()
                            if isinstance(dependency_raw.get('package'), dict):
                                dependency.package_name = dependency_raw.get('package').get('name')
                            dependency.version = dependency_raw.get('version')

                            location.dependency = dependency

                        vulnerability_finding.location = location

                    if isinstance(vulnerability_finding_raw.get('identifiers'), list):
                        identifiers = []
                        for identifier_raw in vulnerability_finding_raw.get('identifiers'):
                            identifier = VulnerabilityIdentifier()
                            identifier.name = identifier_raw.get('name')
                            identifier.external_id = identifier_raw.get('external_id')
                            identifier.external_type = identifier_raw.get('external_type')
                            identifier.url = identifier_raw.get('url')
                            identifiers.append(identifier)
                        vulnerability_finding.identifiers = identifiers
                    vulnerability_findings.append(vulnerability_finding)
                device.vulnerability_findings = vulnerability_findings

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {{device_raw}}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.description = device_raw.get('description')

            if isinstance(device_raw.get('owner'), dict):
                device.owner = device_raw.get('owner').get('username')

            device.name = device_raw.get('name')
            device.first_seen = parse_date(device_raw.get('created_at'))
            device.last_seen = parse_date(device_raw.get('last_activity_at'))

            if isinstance(device_raw.get('extra_members'), list):
                for member in device_raw.get('extra_members'):
                    if not isinstance(member, dict):
                        continue
                    device.add_users(user_sid=member.get('id'), username=member.get('username'))

            self._fill_git_lab_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching GitLab Device for {device_raw}')
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
                logger.exception(f'Problem with fetching GitLab Device for {device_raw}')

    def _fill_git_lab_user_fields(self, user_raw: dict, user: MyUserAdapter):
        try:
            user.web_url = user_raw.get('web_url')
            user.location = user_raw.get('location')
            user.skype = user_raw.get('skype')
            user.linkedin = user_raw.get('linkedin')
            user.twitter = user_raw.get('twitter')
            user.note = user_raw.get('note')
            user.is_private = self._parse_bool(user_raw.get('private_profile'))
            try:
                ip = user_raw.get('current_sign_in_ip')
                user.current_ip = ip
                if ip is not None and isinstance(ip, str):
                    user.current_ip_raw = [ip]
            except Exception:
                pass
            try:
                last_ip = user_raw.get('last_sign_in_ip')
                user.last_ip = last_ip
                if last_ip is not None and isinstance(last_ip, str):
                    user.last_ip_raw = [last_ip]
            except Exception:
                pass
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
                },
                {
                    'name': 'fetch_projects_as_devices',
                    'type': 'bool',
                    'title': 'Fetch projects as devices'
                }
            ],
            'required': [
                'async_chunks',
                'fetch_projects_as_devices'
            ],
            'pretty_name': 'GitLab Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'async_chunks': 50,
            'fetch_projects_as_devices': False
        }

    def _on_config_update(self, config):
        self.__async_chunks = config.get('async_chunks') or 50
        self.__fetch_projects_as_devices = self._parse_bool(config.get('fetch_projects_as_devices')) or False
