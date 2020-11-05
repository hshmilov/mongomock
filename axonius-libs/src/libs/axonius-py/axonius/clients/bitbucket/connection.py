import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from .consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE, URL_BASE_PREFIX, PROJECTS_SUFFIX, REPOS_SUFFIX, \
    COMMITS_SUFFIX, DEFAULT_MAX_COMMITS

logger = logging.getLogger(f'axonius.{__name__}')


class BitbucketConnection(RESTConnection):
    """ rest client for Bitbucket adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            repo = next(self._get_all_repos(should_raise=True), None)
            if not repo:
                raise Exception('0 Repositories returned')

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get(self, *args, **kwargs):
        return super()._get(*args, **kwargs, do_basic_auth=True)

    def _get_projects(self, should_raise=False):
        yield from self._paged_get(PROJECTS_SUFFIX, device_type='projects', should_raise=should_raise)

    def _get_repos_by_project(self, project_name, max_commits=DEFAULT_MAX_COMMITS, should_raise=False):
        repos_url = REPOS_SUFFIX.format(project_name=project_name)
        for repo in self._paged_get(repos_url, device_type='repos', should_raise=should_raise):
            if repo.get('slug') is not None:
                commits = list(
                    self._get_commits_by_repo(repo_suffix=f'{repos_url}/{repo.get("slug")}', max_commits=max_commits))
                repo['extra_commits'] = commits
            yield repo

    def _get_all_repos(self, max_commits=DEFAULT_MAX_COMMITS, should_raise=False):
        for project in self._get_projects(should_raise=should_raise):
            if project.get('key') is None:
                continue
            yield from self._get_repos_by_project(project.get('key'), max_commits=max_commits,
                                                  should_raise=should_raise)

    def _get_commits_by_repo(self, repo_suffix, max_commits=DEFAULT_MAX_COMMITS):
        yield from self._paged_get(COMMITS_SUFFIX.format(repo_suffix=repo_suffix), device_type='commits',
                                   max_devices=max_commits)

    def _paged_get(self, url_suffix: str,
                   device_type: str,
                   max_devices: int = MAX_NUMBER_OF_DEVICES,
                   should_raise=False):
        try:
            total_fetched_devices = 0
            is_last_page = False
            url_params = {
                'limit': DEVICE_PER_PAGE,
                'start': 0
            }

            while not is_last_page:
                response = self._get(url_suffix, url_params=url_params)
                if not (isinstance(response, dict) and isinstance(response.get('values'), list)):
                    logger.warning(f'Received invalid response for devices: {response}')
                    return

                devices = response.get('values')

                for device in devices:
                    if not isinstance(device, dict):
                        continue
                    yield device
                    total_fetched_devices += 1
                    if total_fetched_devices >= max_devices:
                        logger.info(
                            f'Got max {device_type} {max_devices}, got total of {total_fetched_devices} devices')
                        return

                if total_fetched_devices >= max_devices:
                    logger.info(f'Got max {device_type} {max_devices}')
                    break

                next_page = response.get('nextPageStart') or url_params['start'] + DEVICE_PER_PAGE
                url_params['start'] = next_page
                is_last_page = response.get('isLastPage')
                if is_last_page is None:
                    is_last_page = True

            logger.info(f'Got total of {total_fetched_devices} {device_type}')
        except Exception:
            logger.exception(f'Invalid request made while paginating {device_type}')
            if should_raise:
                raise

    # pylint: disable=arguments-differ
    def get_device_list(self, max_commits=DEFAULT_MAX_COMMITS):
        try:
            yield from self._get_all_repos(max_commits=max_commits)
        except RESTException as err:
            logger.exception(str(err))
            raise
