import logging

from typing import Optional

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from slack_adapter.consts import USER_PER_PAGE, TEAM_ID_PER_PAGE, API_PREFIX, URL_ADMIN_TEAM_LIST, \
    URL_ADMIN_USER_LIST, URL_USER_INFO, URL_USER_LIST, MAX_NUMBER_OF_USERS, MAX_NUMBER_OF_TEAM_IDS, URL_BILLING

logger = logging.getLogger(f'axonius.{__name__}')


class SlackConnection(RESTConnection):
    """ rest client for Slack adapter """

    def __init__(self, *args, token: str, is_enterprise: bool, **kwargs):
        super().__init__(*args, url_base_prefix=API_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = token
        self._is_enterprise = is_enterprise
        self._team_ids = set()
        self._user_ids = []

    @staticmethod
    def _move_cursor(response: dict):
        metadata = response.get('response_metadata')
        if metadata and isinstance(metadata, dict):
            cursor = metadata.get('next_cursor')
            if cursor and isinstance(cursor, str):
                return cursor
        return None

    # pylint: disable=too-many-nested-blocks
    def _get_team_ids(self, fetch_one: bool=False):
        try:
            team_ids_counter = 0
            body_params = {
                'limit': 1 if fetch_one else TEAM_ID_PER_PAGE
            }
            while team_ids_counter < MAX_NUMBER_OF_TEAM_IDS:
                response = self._post(URL_ADMIN_TEAM_LIST, body_params=body_params)
                if isinstance(response, dict) and response.get('ok'):
                    teams = response.get('teams')
                    if teams and isinstance(teams, list):
                        for team in teams:
                            if isinstance(team, dict) and team.get('id') and isinstance(team.get('id'), str):
                                self._team_ids.add(team.get('id'))
                                team_ids_counter += 1
                    next_cursor = self._move_cursor(response)
                    if next_cursor:
                        body_params['cursor'] = next_cursor
                    else:
                        break
                else:
                    logger.exception(f'Invalid Slack response for {URL_ADMIN_TEAM_LIST}')
                    raise RESTException(f'Invalid Slack response for {URL_ADMIN_TEAM_LIST}, missing permissions')
            logger.info(f'Fetched total of {team_ids_counter} team IDs')
        except Exception as e:
            logger.exception('Invalid request made while getting team ID')
            raise

    def _connect_enterprise(self):
        self._get_team_ids(fetch_one=True)
        if not self._team_ids:
            raise RESTException('No team ID')
        try:
            body_params = {
                'team_id': list(self._team_ids)[0],
                'limit': 1
            }
            self._post(URL_ADMIN_USER_LIST, body_params=body_params)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _connect_non_enterprise(self):
        try:
            url_params = {
                'limit': 1
            }
            response = self._get(URL_USER_LIST, url_params=url_params)
            if not (isinstance(response, dict) and response.get('ok')):
                raise RESTException(f'Invalid response from: {URL_USER_LIST} {response}')
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _connect(self):
        if not self._token:
            raise RESTException('No token')
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        if self._is_enterprise:
            self._connect_enterprise()
        else:
            self._connect_non_enterprise()

    # pylint: disable=too-many-branches
    def _async_paginated_user_get_enterprise(self, async_chunks: int):
        try:
            self._get_team_ids()
            user_raw_requests = []
            user_counter = 0
            for team_id in list(self._team_ids):
                body_params = {
                    'team_id': team_id,
                    'limit': USER_PER_PAGE
                }
                while user_counter < MAX_NUMBER_OF_USERS:
                    response = self._post(URL_ADMIN_USER_LIST, body_params=body_params)
                    if isinstance(response, dict) and response.get('ok'):
                        users = response.get('users')
                        if users and isinstance(users, list):
                            for user in users:
                                if isinstance(user, dict) and user.get('id'):
                                    self._user_ids.append(user.get('id'))
                                    user_counter += 1
                        next_cursor = self._move_cursor(response)
                        if next_cursor:
                            body_params['cursor'] = next_cursor
                        else:
                            break
                    else:
                        logger.error(f'Invalid Slack response from {URL_ADMIN_USER_LIST}')
                        continue
            for user_id in list(set(self._user_ids)):
                user_raw_requests.append({
                    'name': URL_USER_INFO,
                    'url_params': {'user': user_id}
                })
            for response in self._async_get(user_raw_requests, retry_on_error=True, chunks=async_chunks):
                if not self._is_async_response_good(response):
                    logger.error(f'Async response returned bad: {response}')
                    continue

                if not (isinstance(response, dict) and response.get('user')):
                    logger.warning(f'Invalid response returned: {response}')
                    continue

                if response.get('user') and isinstance(response.get('user'), dict):
                    yield response.get('user')
            logger.info(f'Fetched total of {user_counter} enterprise users')
        except Exception as err:
            logger.exception(f'Invalid request made while paginating enterprise users {str(err)}')
            raise

    def _paginated_user_get_non_enterprise(self):
        billing_info = dict()
        try:
            billing_info_raw = self._get(URL_BILLING)
            billing_info = billing_info_raw.get('billable_info')
        except Exception:
            logger.exception(f'Problem with billing: {billing_info}')
        if not isinstance(billing_info, dict):
            billing_info = dict()
        try:
            user_counter = 0
            url_params = {
                'limit': USER_PER_PAGE
            }
            while user_counter < MAX_NUMBER_OF_USERS:
                response = self._get(URL_USER_LIST, url_params=url_params)
                if isinstance(response, dict) and response.get('ok'):
                    users = response.get('members')
                    if users and isinstance(users, list):
                        for user in users:
                            if isinstance(user, dict):
                                try:
                                    user['billing_info'] = billing_info.get(user['id'])
                                except Exception:
                                    pass
                                yield user
                                user_counter += 1
                    next_cursor = self._move_cursor(response)
                    if next_cursor:
                        url_params['cursor'] = next_cursor
                    else:
                        break
                else:
                    logger.error(f'Invalid Slack response from {URL_USER_LIST} {response}')
                    raise RESTException(f'Invalid Slack response from {URL_USER_LIST} {response}')
            logger.info(f'Fetched total of {user_counter} non-enterprise users')
        except Exception as err:
            logger.exception(f'Invalid request made while paginating non-enterprise users {str(err)}')
            raise

    def get_user_list(self, async_chunks: Optional[int] = None):
        try:
            if self._is_enterprise:
                yield from self._async_paginated_user_get_enterprise(async_chunks)
            else:
                yield from self._paginated_user_get_non_enterprise()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def get_device_list(self):
        pass
