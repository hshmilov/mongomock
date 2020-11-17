import asyncio
import logging
import math
import time
import datetime
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
_MAX_PAGE_COUNT = 10000


class OktaConnection:
    def __init__(self, url: str, api_key: str, https_proxy: str, parallel_requests: int,
                 threshold_percentenge: int):
        url = RESTConnection.build_url(url).strip('/')
        self.__base_url = url
        self.__threshold_percentenge = threshold_percentenge / 100.0
        self.__api_key = api_key
        self.__https_proxy = https_proxy
        self._sleep_between_requests_in_sec = 0
        if not parallel_requests or parallel_requests <= 0:
            parallel_requests = PARALLEL_REQUESTS_DEFAULT
        self.__parallel_requests = parallel_requests

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
        if self._sleep_between_requests_in_sec:
            time.sleep(self._sleep_between_requests_in_sec)
        response = requests.get(forced_url or uritools.urijoin(self.__base_url, api), params=params,
                                headers=headers, proxies={'https': self.__https_proxy}, timeout=get_default_timeout())
        try:
            remaining = int(response.headers.get('X-Rate-Limit-Remaining'))
            limit = int(response.headers.get('X-Rate-Limit-Limit'))
            reset = datetime.datetime.utcfromtimestamp(int(response.headers.get('X-Rate-Limit-Reset')))
            now_time = datetime.datetime.utcnow()
            seconds = 60
            if reset > now_time:
                seconds = (reset - now_time).seconds
            logger.debug(f'remaining: {remaining}')
            logger.debug(f'limit: {limit}')
            logger.debug(f'reset: {reset}')
            logger.debug(f'seconds: {seconds}')
            if remaining / limit < self.__threshold_percentenge:
                logger.info(f'remaining: {remaining}')
                logger.info(f'limit: {limit}')
                logger.info(f'reset: {reset}')
                logger.info(f'seconds: {seconds}')
                time.sleep(seconds)
        except Exception:
            pass
        if response.status_code == 429:
            logger.info(f'Got 429 going to sleep')
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
                                     f' item with no data. Exception: {raw_answer}. Suffix: {url_suffix}')

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

    def _get_extra_data_paginated(self, obj_data, url_suffix, raw_param):
        for i, obj_raw in enumerate(obj_data):
            try:
                if i % 10 == 0:
                    logger.info(f'Got to offset {i} in {url_suffix}')
                item_id = obj_raw['id']
                obj_raw[raw_param] = self._get_url_paginated(url_suffix.format(item_id=item_id))
            except Exception:
                logger.exception(f'Problem with obj raw')

    def _get_url_paginated(self, url):
        obj_data = []
        page_count = 0
        response = self.__make_request(url)
        logger.info(f'Starting to get paginated {url}')
        if isinstance(response.json(), list):
            obj_data.extend(response.json())
        while 'next' in response.links and page_count < _MAX_PAGE_COUNT:
            if page_count % 10 == 0:
                logger.info(f'Got to page {page_count}')
            page_count += 1
            try:
                response = self.__make_request(forced_url=response.links['next']['url'])
                if isinstance(response.json(), list):
                    obj_data.extend(response.json())
            except Exception:
                logger.exception(f'Problem getting group')
                break
        return obj_data

    def _add_object_to_users(self, obj_name):
        users_to_data = dict()
        try:
            obj_data = self._get_url_paginated(f'api/v1/{obj_name}')
            try:
                self._get_extra_data_paginated(obj_data, 'api/v1/' + obj_name + '/{item_id}/users', 'users_raw')
            except Exception:
                logger.exception(f'Problem getting async group')
            for obj_raw in obj_data:
                try:
                    if obj_raw.get('id'):
                        # group_name = (group_raw.get('profile') or {}).get('name')
                        users_data = obj_raw.get('users_raw') or []
                        for user_data_in_obj in users_data:
                            if not isinstance(user_data_in_obj, dict):
                                user_data_in_obj = {}
                            user_id_for_obj = user_data_in_obj.get('id')
                            if user_id_for_obj:
                                if user_id_for_obj not in users_to_data:
                                    users_to_data[user_id_for_obj] = []
                                users_to_data[user_id_for_obj].append(obj_raw)
                except Exception:
                    logger.exception(f'Problem with group raw {obj_raw}')
        except Exception:
            logger.exception('Problem getting groups')
        return users_to_data

    # pylint: disable=R1702,R0912,R0915
    def get_users(self, fetch_apps=False, fetch_factors=False,
                  fetch_logs=False, fetch_groups=True,
                  sleep_between_requests_in_sec=0) -> Iterable[dict]:
        """
        Fetches all users
        :return: iterable of dict
        """

        def get_users_page(api='', forced_url=None):
            response = self.__make_request(api=api, forced_url=forced_url)
            users_page = response.json()
            try:
                if fetch_factors:
                    logger.info(f'Fetching factors')
                    self._get_extra_data_async(users_page, 'api/v1/users/{item_id}/factors', 'factors_raw')
            except Exception:
                logger.exception(f'Problem getting factors')
            for user_raw in users_page:
                if user_raw.get('id') and users_to_group.get(user_raw.get('id')):
                    user_raw['groups_data'] = []
                    for group_raw in users_to_group.get(user_raw.get('id')):
                        if isinstance(group_raw.get('profile'), dict) and group_raw['profile'].get('name'):
                            user_raw['groups_data'].append(group_raw['profile'].get('name'))
                if user_raw.get('id') and users_to_apps.get(user_raw.get('id')):
                    user_raw['apps_data'] = []
                    for app_raw in users_to_apps.get(user_raw.get('id')):
                        app_raw.pop('users_raw', None)
                        user_raw['apps_data'].append(app_raw)
                if user_raw.get('id') and users_to_logs.get((user_raw.get('profile') or {}).get('login')):
                    user_raw['log_data'] = users_to_logs.get((user_raw.get('profile') or {}).get('login'))

            return users_page, response
        if sleep_between_requests_in_sec:
            self._sleep_between_requests_in_sec = sleep_between_requests_in_sec
        users_to_logs = {}
        if fetch_logs:
            logger.info('Starting to fetch logs')
            try:
                for log_raw in self._get_url_paginated('api/v1/logs?'
                                                       'filter=event_type+eq+%22user.authentication.sso%22'):
                    try:
                        target_list = log_raw.get('target')
                        if not isinstance(target_list, list):
                            continue
                        for target_raw in target_list:
                            if not isinstance(target_raw, dict) or not target_raw.get('alternateId'):
                                continue
                            user_id = target_raw['alternateId']
                            if user_id not in users_to_logs:
                                users_to_logs[user_id] = []
                            users_to_logs[user_id].append(log_raw)
                    except Exception:
                        logger.exception(f'Problem with log {log_raw}')
            except Exception:
                logger.exception(f'Problem getting logs')
        users_to_group = dict()
        if fetch_groups:
            logger.info('Starting to get groups')
            users_to_group = self._add_object_to_users('groups')
        users_to_apps = dict()
        if fetch_apps:
            logger.info('Starting to get apps')
            users_to_apps = self._add_object_to_users('apps')
        try:
            logger.info('Starting to get users')
            page_count = 0
            users_page, response = get_users_page(api='api/v1/users')
            yield from users_page
            while 'next' in response.links and page_count < _MAX_PAGE_COUNT:
                users_page, response = get_users_page(forced_url=response.links['next']['url'])
                yield from users_page
                page_count += 1
        except Exception:
            logger.exception('Exception while fetching users')
