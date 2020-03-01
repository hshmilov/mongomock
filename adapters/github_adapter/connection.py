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

    def _get_paginated(self, url, force_full_url=False, _suppress=False):
        url_params = {
            'per_page': consts.DEVICE_PER_PAGE,
            'page': 1  # XXX Yes, Page starts at 1, not 0!
        }
        total_added = 0
        try:
            response = self._get(url,
                                 url_params=url_params,
                                 force_full_url=force_full_url)
        except Exception as e:
            message = f'Failed to get {url} of org {self._org}: {str(e)}'
            if _suppress:
                logger.warning(message)
            else:
                logger.exception(message)
            return
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

    def _get_contributions(self, user_dict, repo_url=None, force_full_url=True, is_org_user=False):
        if not repo_url:
            repo_url = f'{user_dict.get("repos_url")}?type=all'
        repos = list(self._get_paginated(repo_url, force_full_url))
        user_login = user_dict.get('login')
        for repo in repos:
            # For each repo, get contributions url.
            # Get a list of contributions.
            # An org user will have a dictionary mapping all users' contribs to each repo,
            # For a regular user we're only interested in their own contributions to their repos.
            contrib_url = repo.get('contributors_url')
            if not contrib_url:
                continue
            # Get contributions
            try:
                all_contribs = self._get_paginated(contrib_url, force_full_url=True, _suppress=True)
            except RESTException as e:
                message = f'Failed to get contributions from {contrib_url}: {str(e)}'
                logger.warning(message)
                continue
            # Org user has a dictionary mapping all users' contribs to each repo
            if is_org_user:
                repo['x_contribs'] = dict()
            # Go through contributions list for this repo
            for contrib_dict in all_contribs:
                if not contrib_dict:
                    continue
                # Who made this contribution?
                contrib_user = contrib_dict.get('login')
                if not contrib_user:
                    logger.warning(f'Failed to get login info for contributor: {contrib_dict}')
                    continue
                # if we're dealing with the org user, then match each contributing user to their
                # contrib count.
                if is_org_user:
                    repo['x_contribs'][contrib_user] = int(contrib_dict.get('contributions', 0))
                elif contrib_user == user_login:
                    repo['x_contrib_count'] = int(contrib_dict.get('contributions', 0))
                    # For normal users only list their own contribution to the repo.
                    # So if we've found the right entry, break and move on to next repo.
                    break
            # Next repo
        return repos

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
            org_user['x_repositories'] = self._get_contributions(org_user, is_org_user=True)
            yield org_user
        for user_raw in self._get_paginated(f'orgs/{self._org}/members'):
            if user_raw.get('login') == self._user:
                user_raw['x_repositories'] = self._get_contributions(user_raw,
                                                                     f'user/repos?type=all',
                                                                     force_full_url=False)
            else:
                user_raw['x_repositories'] = self._get_contributions(user_raw)
            yield user_raw
