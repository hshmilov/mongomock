import logging
import math
import time
from typing import Iterable
import requests
import uritools
import aiohttp


from axonius.utils.json import from_json
from axonius.async.utils import async_request

logger = logging.getLogger(f'axonius.{__name__}')


PARALLEL_REQUESTS_MAX = 75


class OktaConnection:
    def __init__(self, url: str, api_key: str, fetch_apps: bool):
        self.__base_url = url
        self.__api_key = api_key
        self.__fetch_apps = fetch_apps

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
        return requests.get(forced_url or uritools.urijoin(self.__base_url, api), params=params, headers=headers)

    def is_alive(self):
        """
        Checks if the connection is valid
        :return: True if the connection is good, else returns the (erroneous) response
        """
        response = self.__make_request('api/v1/users', params={'limit': 1})
        if response.status_code == 200:
            return True
        return response

    def _get_apps_async(self, users_page):
        aio_requests = []
        aio_ids = []
        for i, item in enumerate(users_page):
            item_id = item.get('id')
            if not item_id:
                logger.warning('Got user with no id, not yielding')
                continue

            aio_req = dict()
            aio_req['method'] = 'GET'
            aio_req['url'] = uritools.urijoin(self.__base_url,
                                              f'api/v1/apps?'
                                              f'filter=user.id+eq+\'{item_id}\'&expand=user/{item_id}')
            aio_req['timeout'] = (5, 30)

            aio_req['headers'] = {'Authorization': f'SSWS {self.__api_key}'}
            aio_requests.append(aio_req)
            aio_ids.append(i)

        for chunk_id in range(int(math.ceil(len(aio_requests) / PARALLEL_REQUESTS_MAX))):
            logger.debug(f'Async requests: sending '
                         f'{chunk_id * PARALLEL_REQUESTS_MAX} out of {len(aio_requests)}')

            all_answers = async_request(
                aio_requests[PARALLEL_REQUESTS_MAX * chunk_id:
                             PARALLEL_REQUESTS_MAX * (chunk_id + 1)])

            # We got the requests,
            # time to check if they are valid and transform them to what the user wanted.

            for i, raw_answer in enumerate(all_answers):
                request_id_absolute = PARALLEL_REQUESTS_MAX * chunk_id + i
                current_user = users_page[aio_ids[request_id_absolute]]
                try:
                    # The answer could be an exception
                    if isinstance(raw_answer, Exception):
                        logger.error(f'Exception getting tags for request {request_id_absolute}, yielding'
                                     f' device with no tags')

                    # Or, it can be the actual response
                    elif isinstance(raw_answer, tuple) and isinstance(raw_answer[0], str) \
                            and isinstance(raw_answer[1], aiohttp.ClientResponse):
                        text_answer = raw_answer[0]
                        response_object = raw_answer[1]

                        try:
                            response_object.raise_for_status()
                            current_user['apps'] = from_json(text_answer)
                        except aiohttp.ClientResponseError as e:
                            logger.error(f'async error code {e.status} on '
                                         f'request id {request_id_absolute}. '
                                         f'original response is {raw_answer}. Yielding with no apps')
                        except Exception:
                            logger.exception(f'Exception while parsing async response for {text_answer}'
                                             f'. Yielding with no apps')
                    else:
                        msg = f'Got an async response which is not exception or ClientResponse. ' \
                              f'This should never happen! response is {raw_answer}'
                        logger.critical(msg)
                except Exception:
                    msg = f'Error while parsing request {request_id_absolute} - {raw_answer}, continuing'
                    logger.exception(msg)
            # Because Okta block us from doing more than one chunk per minute (usually 100 requests per minute),
            #  we must wait a minute.
            time.sleep(60)

    # pylint: disable=R1702,R0912,R0915
    def get_users(self) -> Iterable[dict]:
        """
        Fetches all users
        :return: iterable of dict
        """
        groups = []
        _MAX_PAGE_COUNT = 1000
        users_to_group = dict()
        page_count = 0
        try:
            response = self.__make_request('api/v1/groups')
            groups.extend(response.json())
            while 'next' in response.links and page_count < _MAX_PAGE_COUNT:
                response = self.__make_request(forced_url=response.links['next']['url'])
                groups.extend(response.json())
            for group_raw in groups:
                try:
                    if group_raw.get('id'):
                        group_id = group_raw.get('id')
                        group_name = (group_raw.get('profile') or {}).get('name')
                        group_data = self.__make_request(f'api/v1/groups/{group_id}/users').json()
                        for user_data_in_group in group_data:
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
            if self.__fetch_apps:
                self._get_apps_async(users_page)
            for user_raw in users_page:
                if user_raw.get('id') and users_to_group.get(user_raw.get('id')):
                    user_raw['groups_data'] = list(users_to_group.get(user_raw.get('id')))
            yield from users_page
            while 'next' in response.links and page_count < _MAX_PAGE_COUNT:
                response = self.__make_request(forced_url=response.links['next']['url'])
                users_page = response.json()
                if self.__fetch_apps:
                    self._get_apps_async(users_page)
                for user_raw in users_page:
                    if user_raw.get('id'):
                        user_raw['groups_data'] = list(users_to_group.get(user_raw.get('id')))
                yield from users_page
                page_count += 1
        except Exception:
            logger.exception('Exception while fetching users')
