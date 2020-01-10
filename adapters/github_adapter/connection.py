import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from github_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class GithubConnection(RESTConnection):
    """ rest client for Github adapter """

    def __init__(self, *args, token='', org='', **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = token
        self._org = org

    def _get_self_user(self):
        try:
            user_info = self._get('user')
            self._user = user_info.get('login')
            return user_info
        except RESTException as e:
            self._user = None
            logger.exception(f'Failed to get self user, auth probably incorrect: {str(e)}')
            raise

    def _get_paginated(self, url, force_full_url=False):
        url_params = {
            'per_page': consts.DEVICE_PER_PAGE,
            'page': 1  # XXX Yes, Page starts at 1, not 0!
        }
        total_added = 0
        response = None
        try:
            response = self._get(url,
                                 url_params=url_params,
                                 force_full_url=force_full_url)
        except RESTException as e:
            message = f'Failed to get {url} of org {self._org}: {str(e)}'
            logger.exception(message)
            yield {}
        while response:
            yield from response
            total_added += len(response)
            logger.debug(f'Yielded {total_added} results so far')
            if total_added >= consts.MAX_NUMBER_OF_DEVICES:
                logger.warning(f'Stopping after {total_added} results, maximum is '
                               f'{consts.MAX_NUMBER_OF_DEVICES}.')
                break
            url_params['page'] += 1
            try:
                response = self._get(url,
                                     url_params=url_params,
                                     force_full_url=force_full_url)
            except RESTException as e:
                message = f'Failed to get page {url_params["page"]} results of org ' \
                          f'{self._org}: {str(e)}'
                logger.exception(message)
                break

    def _connect(self):
        if not self._token or not self._org:
            raise RESTException('No auth token or organization')
        self._session_headers['Authorization'] = f'token {self._token}'
        self._get_self_user()
        self._get(f'orgs/{self._org}')

    def get_device_list(self):
        # not a device adapter, so no need to do anything?
        yield {}

    def get_users(self):
        try:
            org_user = self._get(f'orgs/{self._org}')
        except RESTException as e:
            logger.error(f'Failed to fetch Org User information: {str(e)}')
        else:
            repo_url = org_user.get('repos_url')
            org_user['x_repositories'] = list(self._get_paginated(f'{repo_url}?type=all', force_full_url=True))
            yield org_user
        for user_raw in self._get_paginated(f'orgs/{self._org}/members'):
            if user_raw.get('login') == self._user:
                user_raw['x_repositories'] = list(self._get_paginated(f'user/repos?type=all'))
            else:
                repo_url = user_raw.get('repos_url')
                user_raw['x_repositories'] = list(self._get_paginated(f'{repo_url}?type=all', force_full_url=True))
            yield user_raw
