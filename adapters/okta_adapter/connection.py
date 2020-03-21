import asyncio
import logging
import math
import time
from typing import Iterable
import requests
import uritools
import aiohttp


from axonius.utils.json import from_json
from axonius.async.utils import async_request
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.consts import get_default_timeout

logger = logging.getLogger(f'axonius.{__name__}')


PARALLEL_REQUESTS_DEFAULT = 75
DEFAULT_SLEEP_TIME = 60


class OktaConnection:
    def __init__(self, url: str, api_key: str, https_proxy: str):
        url = RESTConnection.build_url(url).strip('/')
        self.__base_url = url
        self.__api_key = api_key
        self.__parallel_requests = PARALLEL_REQUESTS_DEFAULT
        self.__https_proxy = https_proxy

    # pylint: disable=W0102
    def __make_request(self, api='', params={}, forced_url=None):
        """
        Makes a request to the Okta service.
        Either 'api' or 'forced_url' must be provided.
        :param api: must be relative (i.e. 'api/v1/users')
        :param params: url GET parameters
        :param forced_url: must be absolute (i.e. 'https://axonius.okta.com/api/v1/users?after=2&limit=1')
        :return: response
        """
        assert bool(api) != bool(forced_url)
        headers = {
            'Authorization': f'SSWS {self.__api_key}'
        }
        response = requests.get(forced_url or uritools.urijoin(self.__base_url, api), params=params,
                                headers=headers, proxies={'https': self.__https_proxy}, timeout=get_default_timeout())
        if response.status_code == 429:
            time.sleep(DEFAULT_SLEEP_TIME)
            response = requests.get(forced_url or uritools.urijoin(self.__base_url, api), params=params,
                                    headers=headers, proxies={'https': self.__https_proxy},
                                    timeout=get_default_timeout())
        response.raise_for_status()
        return response

    def is_alive(self):
        """
        Checks if the connection is valid
        :return: True if the connection is good, else returns the (erroneous) response
        """
        response = self.__make_request('api/v1/users', params={'limit': 1})
        if response.status_code == 200:
            return True
        raise Exception(f'Probelm fetching users. Got: {response.content}')

    async def handle_429(self, response: aiohttp.ClientResponse):
        """
        Handle 429 responses for async requests
        :param response: http response
        :return: None
        """
        logger.info(f'Got 429 response, waiting for {DEFAULT_SLEEP_TIME} seconds.')
        await asyncio.sleep(DEFAULT_SLEEP_TIME)

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _get_extra_data_async(self, items_page, url_suffix, raw_param):
        aio_requests = []
        aio_ids = []
        for i, item in enumerate(items_page):
            item_id = item.get('id')
            if not item_id:
                logger.warning('Got user with no id, not yielding')
                continue

            aio_req = dict()
            aio_req['method'] = 'GET'
            aio_req['url'] = uritools.urijoin(self.__base_url,
                                              url_suffix.format(item_id=item_id))
            aio_req['timeout'] = (5, 30)

            aio_req['headers'] = {'Authorization': f'SSWS {self.__api_key}'}
            if self.__https_proxy:
                aio_req['proxy'] = self.__https_proxy
                https_prefix = 'https://'
                http_prefix = 'http://'
                if aio_req['proxy'].startswith(https_prefix):
                    aio_req['proxy'] = aio_req['proxy'][len(https_prefix):]

                if not aio_req['proxy'].startswith(http_prefix):
                    aio_req['proxy'] = http_prefix + aio_req['proxy']
            aio_requests.append(aio_req)
            aio_ids.append(i)

        for chunk_id in range(int(math.ceil(len(aio_requests) / self.__parallel_requests))):
            logger.debug(f'Async requests: sending '
                         f'{chunk_id * self.__parallel_requests} out of {len(aio_requests)}')

            all_answers = async_request(
                aio_requests[self.__parallel_requests * chunk_id:
                             self.__parallel_requests * (chunk_id + 1)], handle_429_function=self.handle_429)

            # We got the requests,
            # time to check if they are valid and transform them to what the user wanted.

            for i, raw_answer in enumerate(all_answers):
                request_id_absolute = self.__parallel_requests * chunk_id + i
                current_item = items_page[aio_ids[request_id_absolute]]
                try:
                    # The answer could be an exception
                    if isinstance(raw_answer, Exception):
                        logger.error(f'Exception getting extra data for request {request_id_absolute}, yielding'
                                     f' item with no data')

                    # Or, it can be the actual response
                    elif isinstance(raw_answer, tuple) and isinstance(raw_answer[0], str) \
                            and isinstance(raw_answer[1], aiohttp.ClientResponse):
                        text_answer = raw_answer[0]
                        response_object = raw_answer[1]

                        try:
                            response_object.raise_for_status()
                            current_item[raw_param] = from_json(text_answer)
                        except aiohttp.ClientResponseError as e:
                            logger.error(f'async error code {e.status} on '
                                         f'request id {request_id_absolute}. '
                                         f'original response is {raw_answer}. Yielding with no data')
                        except Exception:
                            logger.exception(f'Exception while parsing async response for {text_answer}'
                                             f'. Yielding with no data')
                    elif raw_answer:
                        msg = f'Got an async response which is not exception or ClientResponse. ' \
                              f'This should never happen! response is {raw_answer}'
                        logger.critical(msg)
                except Exception:
                    msg = f'Error while parsing request {request_id_absolute} - {raw_answer}, continuing'
                    logger.exception(msg)

    # pylint: disable=R1702,R0912,R0915
    def get_users(self, parallel_requests, fetch_apps=False, fetch_factors=False) -> Iterable[dict]:
        """
        Fetches all users
        :return: iterable of dict
        """
        groups = []
        _MAX_PAGE_COUNT = 1000
        if parallel_requests <= 0:
            parallel_requests = PARALLEL_REQUESTS_DEFAULT
        self.__parallel_requests = parallel_requests
        users_to_group = dict()
        page_count = 0
        try:
            response = self.__make_request('api/v1/groups')
            if isinstance(response.json(), list):
                groups.extend(response.json())
            while 'next' in response.links and page_count < _MAX_PAGE_COUNT:
                try:
                    response = self.__make_request(forced_url=response.links['next']['url'])
                    if isinstance(response.json(), list):
                        groups.extend(response.json())
                except Exception:
                    logger.exception(f'Problem getting group')
                    break
            try:
                self._get_extra_data_async(groups, 'api/v1/groups/{item_id}/users', 'users_raw')
            except Exception:
                logger.exception(f'Problem getting async group')
            for group_raw in groups:
                try:
                    if group_raw.get('id'):
                        group_name = (group_raw.get('profile') or {}).get('name')
                        group_data = group_raw.get('users_raw') or []
                        for user_data_in_group in group_data:
                            if not isinstance(user_data_in_group, dict):
                                user_data_in_group = {}
                            user_id_for_group = user_data_in_group.get('id')
                            if user_id_for_group:
                                if user_id_for_group not in users_to_group:
                                    users_to_group[user_id_for_group] = set()
                                if group_name not in users_to_group[user_id_for_group]:
                                    users_to_group[user_id_for_group].add(group_name)

                except Exception:
                    logger.exception(f'Problem with group raw {group_raw}')
        except Exception:
            logger.exception('Problem getting groups')
        try:
            page_count = 0
            response = self.__make_request('api/v1/users')
            users_page = response.json()
            try:
                if fetch_apps:
                    self._get_extra_data_async(users_page,
                                               'api/v1/apps?filter=user.id+eq+\"{item_id}\"&expand=user/{item_id}',
                                               'apps')
            except Exception:
                logger.exception('Problem getting apps')
            try:
                if fetch_factors:
                    self._get_extra_data_async(users_page, 'api/v1/users/{item_id}/factors', 'factors_raw')
            except Exception:
                logger.exception(f'Problem getting factors')
            for user_raw in users_page:
                if user_raw.get('id') and users_to_group.get(user_raw.get('id')):
                    user_raw['groups_data'] = list(users_to_group.get(user_raw.get('id')))
            yield from users_page
            while 'next' in response.links and page_count < _MAX_PAGE_COUNT:
                response = self.__make_request(forced_url=response.links['next']['url'])
                users_page = response.json()
                try:
                    if fetch_apps:
                        self._get_extra_data_async(users_page,
                                                   'api/v1/apps?filter=user.id+eq+\"{item_id}\"&expand=user/{item_id}',
                                                   'apps')
                except Exception:
                    logger.exception('Problem getting apps')
                try:
                    if fetch_factors:
                        self._get_extra_data_async(users_page, 'api/v1/users/{item_id}/factors', 'factors_raw')
                except Exception:
                    logger.exception(f'Problem getting factors')
                for user_raw in users_page:
                    if user_raw.get('id') and users_to_group.get(user_raw.get('id')):
                        user_raw['groups_data'] = list(users_to_group.get(user_raw.get('id')))
                yield from users_page
                page_count += 1
        except Exception:
            logger.exception('Exception while fetching users')
