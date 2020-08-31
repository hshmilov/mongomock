import logging

from typing import Optional

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import int_or_none
from git_lab_adapter.consts import API_URL_PREFIX, DEVICE_PER_PAGE, MAX_PAGES_GROUPS, MAX_PAGES_PROJECTS, \
    GROUPS_PREFIX, EXTRA_GROUPS, EXTRA_PROJECTS, MAX_NUMBER_OF_USERS, MAX_PROJECT_BY_USER_COUNT, \
    MAX_PAGES_VULNERABILTY_FINDINGS, MAX_NUMBER_OF_PROJECTS, WHITE_LIST_PROJECTS_LINKS

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class GitLabConnection(RESTConnection):
    """ rest client for GitLab adapter
    API docs do not document, but 1==0 for pages! (Tested, same data), in API docs default page is 1.
    Docs here: https://docs.gitlab.com/ee/api/
    Explanation: The token user may be a member of groups and subgroups and also be included in projects outside of
    groups. Each group can contain subgroups / projects (each subgroup may contain projects / subgroups etc..).
    Basic flow: 1. Get all groups and subgroups.
                2. Get all membership projects
                3. Get all projects of the groups and subgroups (from stage 1)
                4. Get all users from groups, subgroups (stage 1) and projects (stage 2 and 3)
                5. Fetch all the users information
    """

    def __init__(self, *args, token: str, **kwargs):
        super().__init__(*args, url_base_prefix=API_URL_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = token

    def _connect(self):
        if not self._token:
            raise RESTException('No token')

        try:
            self._session_headers = {
                'Authorization': f'Bearer {self._token}'
            }
            url_params = {
                'page': 1,  # Default is page 1 (page 0 == 1), see docs.
                'per_page': 1
            }
            self._get(GROUPS_PREFIX, url_params=url_params)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    # pylint: disable=arguments-differ
    def get_device_list(self, fetch_projects_as_devices: bool = False):
        try:
            if fetch_projects_as_devices:
                yield from self._paginated_get_devices()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _get_groups_by_id(self):
        try:
            groups_by_id = {}

            for current_page in range(1, MAX_PAGES_GROUPS + 1):
                url_params = {
                    'page': current_page,
                    'per_page': DEVICE_PER_PAGE
                }
                response = self._get(GROUPS_PREFIX, url_params=url_params)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while getting groups {response}')
                    return {}

                for group in response:
                    if isinstance(group, dict) and group.get('id'):
                        groups_by_id[group.get('id')] = group

                if len(response) != DEVICE_PER_PAGE:
                    logger.debug(f'Got {(current_page * DEVICE_PER_PAGE) - (DEVICE_PER_PAGE - len(response))}'
                                 f' groups in total')
                    break

            logger.info(f'Got {(current_page * DEVICE_PER_PAGE) - (DEVICE_PER_PAGE - len(response))} groups in total')
            return groups_by_id
        except Exception:
            logger.exception(f'Invalid request made while getting groups')
            return {}

    # pylint: disable=too-many-nested-blocks, too-many-branches
    def _get_projects_users(self, projects_by_id: dict):
        try:
            project_users_by_id = {}
            total_projects_users = 0

            for project_id, project in projects_by_id.items():
                url = f'projects/{project_id}/members/all'
                url_params = {
                    'page': 1,
                    'per_page': DEVICE_PER_PAGE
                }
                response = self._get(url, url_params=url_params)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while getting project users {response}')
                    break

                for user in response:
                    if isinstance(user, dict) and user.get('id'):
                        if not project_users_by_id.get(user.get('id')):
                            project_users_by_id[user.get('id')] = user
                            total_projects_users += 1
                        if not project_users_by_id[user.get('id')].get(EXTRA_PROJECTS):
                            project_users_by_id[user.get('id')][EXTRA_PROJECTS] = [(project_id, project.get('name'))]
                        else:
                            project_users_by_id[user.get('id')][EXTRA_PROJECTS].append(
                                (project_id, project.get('name')))

                while len(response) == DEVICE_PER_PAGE:
                    url_params['page'] += 1
                    response = self._get(url, url_params=url_params)
                    if not isinstance(response, list):
                        logger.warning(f'Received invalid response while paginating project users {response}')
                        break

                    for user in response:
                        if total_projects_users >= MAX_NUMBER_OF_USERS:
                            break
                        if isinstance(user, dict) and user.get('id'):
                            if not project_users_by_id.get(user.get('id')):
                                project_users_by_id[user.get('id')] = user
                                total_projects_users += 1
                            if not project_users_by_id[user.get('id')].get(EXTRA_PROJECTS):
                                project_users_by_id[user.get('id')][EXTRA_PROJECTS] = [
                                    (project_id, project.get('name'))]
                            else:
                                project_users_by_id[user.get('id')][EXTRA_PROJECTS].append(
                                    (project_id, project.get('name')))

            return project_users_by_id
        except Exception:
            logger.exception(f'Invalid request made while getting project users')
            return {}

    def _get_membership_projects(self):
        try:
            membership_projects_by_id = {}
            for current_page in range(1, MAX_PAGES_PROJECTS + 1):
                url_params = {
                    'page': current_page,
                    'per_page': DEVICE_PER_PAGE,
                    'membership': True
                }

                response = self._get('projects', url_params=url_params)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while getting membership projects {response}')
                    return membership_projects_by_id

                for membership_project in response:
                    if isinstance(membership_project, dict) and membership_project.get('id'):
                        membership_projects_by_id[membership_project.get('id')] = membership_project

                if len(response) != DEVICE_PER_PAGE:
                    logger.debug(f'Got {(current_page * DEVICE_PER_PAGE) - (DEVICE_PER_PAGE - len(response))} '
                                 f'membership projects')
                    break

            return membership_projects_by_id
        except Exception:
            logger.exception(f'Invalid request made while getting project users')
            return {}

    def _get_groups_projects(self, groups_by_id: dict):
        try:
            projects_by_id = {}
            total_projects = 0

            for group_id, group in groups_by_id.items():
                url = f'groups/{group_id}/projects'
                url_params = {
                    'page': 1,
                    'per_page': DEVICE_PER_PAGE
                }
                response = self._get(url, url_params=url_params)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while getting group projects {response}')
                    break

                for project in response:
                    if isinstance(project, dict) and project.get('id'):
                        if not projects_by_id.get(project.get('id')):
                            projects_by_id[project.get('id')] = project
                            total_projects += 1
                        if not projects_by_id[project.get('id')].get(EXTRA_GROUPS):
                            projects_by_id[project.get('id')][EXTRA_GROUPS] = [(group_id, group.get('name'))]
                        else:
                            projects_by_id[project.get('id')][EXTRA_GROUPS].append((group_id, group.get('name')))

                while len(response) == DEVICE_PER_PAGE:
                    url_params['page'] += 1
                    response = self._get(url, url_params=url_params)
                    if not isinstance(response, list):
                        logger.warning(f'Received invalid response while paginating group projects {response}')
                        break

                    for project in response:
                        if total_projects >= MAX_PROJECT_BY_USER_COUNT:
                            break
                        if isinstance(project, dict) and project.get('id'):
                            if not projects_by_id.get(project.get('id')):
                                projects_by_id[project.get('id')] = project
                                total_projects += 1
                            if not projects_by_id[project.get('id')].get(EXTRA_GROUPS):
                                projects_by_id[project.get('id')][EXTRA_GROUPS] = [(group_id, group.get('name'))]
                            else:
                                projects_by_id[project.get('id')][EXTRA_GROUPS].append((group_id, group.get('name')))

            logger.info(f'Got total of {total_projects} projects')
            return projects_by_id
        except Exception:
            logger.exception(f'Invalid request made while getting groups projects')
            return {}

    # pylint: disable=too-many-nested-blocks, too-many-branches
    def _get_groups_users(self, groups_by_id: dict):
        try:
            group_users_by_id = {}
            total_group_users = 0

            for group_id, group in groups_by_id.items():
                url = f'groups/{group_id}/members'
                url_params = {
                    'page': 1,
                    'per_page': DEVICE_PER_PAGE
                }
                response = self._get(url, url_params=url_params)
                if not isinstance(response, list):
                    logger.warning(f'Received invalid response while getting users groups {response}')
                    break

                for user in response:
                    if isinstance(user, dict) and user.get('id'):
                        if not group_users_by_id.get(user.get('id')):
                            group_users_by_id[user.get('id')] = user
                            total_group_users += 1
                        if not group_users_by_id[user.get('id')].get(EXTRA_GROUPS):
                            group_users_by_id[user.get('id')][EXTRA_GROUPS] = [(group_id, group.get('name'))]
                        else:
                            group_users_by_id[user.get('id')][EXTRA_GROUPS].append((group_id, group.get('name')))

                while len(response) == DEVICE_PER_PAGE:
                    url_params['page'] += 1
                    response = self._get(url, url_params=url_params)
                    if not isinstance(response, list):
                        logger.warning(f'Received invalid response while paginating users groups {response}')
                        break

                    for user in response:
                        if total_group_users >= MAX_NUMBER_OF_USERS:
                            break
                        if isinstance(user, dict) and user.get('id'):
                            if not group_users_by_id.get(user.get('id')):
                                group_users_by_id[user.get('id')] = user
                                total_group_users += 1
                            if not group_users_by_id[user.get('id')].get(EXTRA_GROUPS):
                                group_users_by_id[user.get('id')][EXTRA_GROUPS] = [(group_id, group.get('name'))]
                            else:
                                group_users_by_id[user.get('id')][EXTRA_GROUPS].append((group_id, group.get('name')))

            logger.info(f'Got total of {total_group_users} users from groups')
            return group_users_by_id
        except Exception:
            logger.exception(f'Invalid request made while getting users group')
            return {}

    def _paginated_async_get_users(self, async_chunks: int):
        # Get all groups including subgroups
        groups_by_id = self._get_groups_by_id()

        # Get all the projects (from groups and from membership)
        membership_projects_by_id = self._get_membership_projects()
        groups_projects_by_id = self._get_groups_projects(groups_by_id)
        # runing UPDATE - groups_project run over membership_project if have the same project id
        # groups_projects have extra information - each project also contain all the groups he is in
        membership_projects_by_id.update(groups_projects_by_id)
        total_projects_by_id = membership_projects_by_id

        # Get all users inside all group
        groups_users_by_id = self._get_groups_users(groups_by_id)

        # Get all the users inside the projects
        projects_users_by_id = self._get_projects_users(total_projects_by_id)

        user_raw_requests = []
        for group_user_id in groups_users_by_id:
            user_raw_requests.append({
                'name': f'users/{group_user_id}',
            })

        for project_user_id in projects_users_by_id:
            if project_user_id not in groups_users_by_id:
                user_raw_requests.append({
                    'name': f'users/{project_user_id}',
                })

        for response in self._async_get(user_raw_requests, retry_on_error=True, chunks=async_chunks):
            if not self._is_async_response_good(response):
                logger.error(f'Async response returned bad, its {response}')
                continue

            if not (isinstance(response, dict) and response.get('id')):
                logger.warning(f'Invalid response returned: {response}')
                continue

            user_id = response.get('id')

            group_user_id = groups_users_by_id.pop(user_id, None)
            if group_user_id:
                response[EXTRA_GROUPS] = group_user_id.get(EXTRA_GROUPS)

            project_user_id = projects_users_by_id.pop(user_id, None)
            if project_user_id:
                response[EXTRA_PROJECTS] = project_user_id.get(EXTRA_PROJECTS)

            yield response

    def get_user_list(self, async_chunks: Optional[int] = None):
        try:
            yield from self._paginated_async_get_users(async_chunks)
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _get_vulnerability_findings_by_id(self, project_id):
        vulnerability_findings = []
        try:
            url_params = {
                'page': 1,
                'per_page': DEVICE_PER_PAGE,
                'scope': 'all'
            }

            response = self._get(f'projects/{project_id}/vulnerability_findings', url_params=url_params,
                                 return_response_raw=True, use_json_in_response=False)

            number_of_pages = int_or_none(response.headers.get('X-Total-Pages'))
            if not number_of_pages:
                logger.warning(f'Could not find X-Total-Pages in response header {response}')
                return vulnerability_findings

            if number_of_pages > MAX_PAGES_VULNERABILTY_FINDINGS:
                logger.info(
                    f'Number of pages is bigger then max pages. number of pages: {number_of_pages},'
                    f' max pages: {MAX_PAGES_VULNERABILTY_FINDINGS}')
                number_of_pages = MAX_PAGES_VULNERABILTY_FINDINGS

            response = response.json()

            if not isinstance(response, list):
                logger.warning(f'Received invalid response while getting users groups {response}')
                return vulnerability_findings

            # Filter out dismissed (remediated) vulnerabilities
            vulnerability_findings.extend([vulnerability_finding for vulnerability_finding in response if
                                           not vulnerability_finding.get('dismissal_feedback')])

            for _ in range(2, number_of_pages):
                url_params['page'] += 1
                response = self._get(f'projects/{project_id}/vulnerability_findings', url_params=url_params)
                if not isinstance(response, list):
                    logger.warning(
                        f'Received invalid response while paginating users'
                        f' groups {response}, page number: {url_params["page"]}')
                    continue

                vulnerability_findings.extend([vulnerability_finding for vulnerability_finding in response if
                                               not vulnerability_finding.get('dismissal_feedback')])
        except Exception as e:
            logger.warning(f'Error getting vulnerability findings, Error: {str(e)}')

        logger.info(f'Done fetching {len(vulnerability_findings)} vulnerability findings for project {project_id}')
        return vulnerability_findings

    def _paginated_get_devices(self):
        try:
            number_of_projects = 0
            # Get all groups including subgroups
            groups_by_id = self._get_groups_by_id()

            # Get all the projects (from groups and from membership)
            membership_projects_by_id = self._get_membership_projects()
            groups_projects_by_id = self._get_groups_projects(groups_by_id)
            # running UPDATE - groups_project run over membership_project if have the same project id
            # groups_projects have extra information - each project also contain all the groups he is in
            membership_projects_by_id.update(groups_projects_by_id)
            total_projects_by_id = membership_projects_by_id

            for project_id, project in total_projects_by_id.items():
                if number_of_projects >= MAX_NUMBER_OF_PROJECTS:
                    break

                if isinstance(project.get('_links'), dict):
                    links = project.get('_links')
                    links = {name: link for name, link in links.items() if name in WHITE_LIST_PROJECTS_LINKS}

                    requests = [{'name': link} for link in links.values()]

                    for name, response in zip(links.keys(), self._async_get(requests)):
                        project[f'extra_{name}'] = response

                project['extra_vulnerability_findings'] = self._get_vulnerability_findings_by_id(project_id)
                number_of_projects += 1
                yield project
        except RESTException as err:
            logger.exception(f'Error happened while getting projects {str(err)}')
            return
