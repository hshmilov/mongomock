import asyncio
import getpass
import json
import sys
import logging
import time
from typing import Optional

import aiohttp
import math
import requests
import uritools

logging.basicConfig(level=logging.DEBUG)

from async_utils import async_request, async_http_request

SECRETS_FILE = f'{__file__}.secrets'

PAGE_SIZE = 500
MAX_DEVICES_NUMBER = 200000
MAX_APPS_NUMBER = 10000
ENROLLED_DEVICE = 'Enrolled Device'
NOT_ENROLLED_DEVICE = 'Not Enrolled Device'

ERROR_MUTED_SUBENDPOINTS = ['tags', 'profiles', 'notes']

ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE = 50
# default sleep time on 429 error
DEFAULT_429_SLEEP_TIME = 60
# max sleep time - 2 hours
MAX_SLEEP_TIME = 60 * 60 * 2
# max async errors retries
MAX_ASYNC_RETRIES = 3
# sleep time on connection refused error on async request
ASYNC_ERROR_SLEEP_TIME = 3

logger = logging.getLogger(f'')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('[%(levelname)s] - %(asctime)s: %(message)s'))
logger.addHandler(ch)


class AirwatchConnection:
    def __init__(
            self,
            domain,
            api_key,
            username,
            password,
    ):

        self._domain = domain
        self._api_key = api_key
        self._username = username
        self._password = password

        if not any(x in domain for x in ['http://', 'https://']):
            raise ValueError(f'Domain must contain http:// or https://')

        self._url_base = f'{domain.strip().rstrip("/")}/api/'
        self._session_headers = {
            'User-Agent': 'Fiddler',
            'aw-tenant-code': api_key,
            'Accept': 'application/xml'
        }
        self._proxies = {

        }

    def _async_get(self, list_of_requests,
                   chunks=ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE,
                   max_retries=MAX_ASYNC_RETRIES,
                   retry_on_error=False,
                   retry_sleep_time=ASYNC_ERROR_SLEEP_TIME):
        return self._do_async_request('GET', list_of_requests, chunks,
                                      max_retries, retry_on_error, retry_sleep_time)

    def _get_url_request(self, request_name):
        """ Builds and returns the full url for the request

        :param request_name: the request name
        :return: the full request url
        """
        if request_name.startswith('/'):
            raise ValueError(f'Url with double / : {self._url_base} AND {request_name}')
        return uritools.urijoin(self._url_base, request_name)

    @staticmethod
    def _is_async_response_good(response):
        return not isinstance(response, Exception)

    def create_async_dict(self, req, method):
        """
        :param dict req:    convert RestConnection request dictionary to a dictionary contains aiohttp request params
        :param str method:  http method
        :return: dictionary
        """
        aio_req = dict()
        aio_req['method'] = method
        if req.get('callback'):
            aio_req['callback'] = req.get('callback')
        # Build url
        if req.get('force_full_url', False) is True:
            aio_req['url'] = req['name']
        else:
            aio_req['url'] = self._get_url_request(req['name'])

        # Take care of url params
        url_params = req.get('url_params')
        if url_params is not None:
            aio_req['params'] = url_params

        # Take care of body params
        body_params = req.get('body_params')
        if body_params is not None:
            if req.get('use_json_in_body', True) is True:
                aio_req['json'] = body_params
            else:
                aio_req['data'] = body_params

        # Take care of auth
        if req.get('do_basic_auth', False) is True:
            aio_req['auth'] = (self._username, self._password)
        if req.get('do_digest_auth') is not None:
            raise ValueError(f'Async requests do not support digest auth')

        # Take care of headers, timeout and ssl verification
        aio_req['headers'] = self._session_headers.copy()
        aio_req['headers'].update(self._session_headers)
        if req.get('headers'):
            aio_req['headers'].update(req.get('headers'))
        aio_req['timeout'] = (5, 300)
        aio_req['verify_ssl'] = False

        # Take care of proxy. aiohttp doesn't allow us to try both proxies, we need to prefer one of them.
        if self._proxies.get('https'):
            aio_req['proxy'] = self._proxies['https']
        elif self._proxies.get('http'):
            aio_req['proxy'] = self._proxies['http']

        if aio_req.get('proxy'):
            # aiohttp doesn't support https proxy, but it does support https proxy over http CONNECT.
            # always try to prepand http://
            https_prefix = 'https://'
            http_prefix = 'http://'

            if aio_req['proxy'].startswith(https_prefix):
                aio_req['proxy'] = aio_req['proxy'][len(https_prefix):]

            if not aio_req['proxy'].startswith(http_prefix):
                aio_req['proxy'] = http_prefix + aio_req['proxy']

        return aio_req

    def _do_single_async_request(self, method, request, session):
        """
        create a single http request, return an awaitable object
        :param str method:      Http method
        :param dict request:    request dictionary to send
        :param aiohttp.ClientSession session:   aiohttp session
        :return: async async_http_request
        """
        req = self.create_async_dict(request, method)
        return async_http_request(session, **req)

    @staticmethod
    def handle_sync_429_default(response: requests.Response):
        sleep_time = 60
        retry_after = response.headers.get('Retry-After')
        try:
            if retry_after:
                sleep_time = int(retry_after)
        except Exception:
            logger.warning(f'handle_sync_429: Bad retry-after value: {str(retry_after)}')

        logger.info(f'Got 429. Sleeping for {sleep_time} seconds')
        time.sleep(sleep_time)

    async def handle_429(self, response: aiohttp.ClientResponse):
        """
        function for handling 429 - Too many requests response.
        override this function for custom handling
        :param response: http response object
        :param err: aiohttp response error
        :return: None
        """
        try:
            sleep_time = DEFAULT_429_SLEEP_TIME
            if response and response.headers:
                # usually servers replies with 'Retry-After' header on 429 responses.
                sleep_time = int(response.headers.get('Retry-After', DEFAULT_429_SLEEP_TIME))
                if sleep_time > MAX_SLEEP_TIME:
                    sleep_time = MAX_SLEEP_TIME
            logger.info(f'Got 429 response, waiting for {sleep_time} seconds.')
            await asyncio.sleep(sleep_time)
        except Exception as e:
            logger.error(f'Error getting retry header from 429 response: {e}. sleeping for {DEFAULT_429_SLEEP_TIME}')
            await asyncio.sleep(DEFAULT_429_SLEEP_TIME)

    # pylint: disable=R0915
    def _do_async_request(self, method, list_of_requests, chunks,
                          max_retries=MAX_ASYNC_RETRIES,
                          retry_on_error=False,
                          retry_sleep_time=ASYNC_ERROR_SLEEP_TIME):
        """
        makes requests asynchronously. list_of_requests is a dict of parameters you would normally pass to _do_request.
        :param method:
        :param list_of_requests:
        :param chunks: the amount of chunks to send in parallel. If the total amount of requests is over, chunks will be
                       used. e.g., if chunks=100 and we have 150 requests, 100 will be parallel (asyncio) and then 50.
        :return:
        """
        #
        #   Remember to change _do_request when adding/removing functionality here!
        #

        # Transform regular to aio requests
        aio_requests = []

        for req in list_of_requests:
            aio_requests.append(self.create_async_dict(req, method))
        # Now that we have built the new requests, try to asynchronously get them.
        for chunk_id in range(int(math.ceil(len(aio_requests) / chunks))):
            logger.debug(f'Async requests: sending {chunk_id * chunks} out of {len(aio_requests)}')
            all_answers = async_request(aio_requests[chunks * chunk_id: chunks * (chunk_id + 1)],
                                        self.handle_429, cert=None,
                                        max_retries=max_retries,
                                        retry_on_error=retry_on_error,
                                        retry_sleep_time=retry_sleep_time)

            # We got the requests, time to check if they are valid and transform them to what the user wanted.
            for i, raw_answer in enumerate(all_answers):
                answer_text = None
                request_id_absolute = chunks * chunk_id + i
                # The answer could be an exception
                if isinstance(raw_answer, Exception):
                    yield raw_answer

                # Or, it can be the actual response
                elif isinstance(raw_answer, tuple) and \
                        isinstance(raw_answer[0], str) and isinstance(raw_answer[1], aiohttp.ClientResponse):
                    try:
                        answer_text = raw_answer[0]
                        response_object = raw_answer[1]

                        response_object.raise_for_status()
                        if list_of_requests[request_id_absolute].get('return_response_raw', False) is True:
                            yield response_object
                        elif list_of_requests[request_id_absolute].get('use_json_in_response', True) is True:
                            yield json.loads(answer_text)  # from_json also handles datetime with json.loads doesn't
                        else:
                            yield answer_text
                    except aiohttp.ClientResponseError as e:
                        try:
                            rp = json.loads(answer_text)  # from_json also handles datetime with json.loads doesn't
                        except Exception:
                            rp = str(answer_text)
                        error_on = list_of_requests[request_id_absolute]['name']
                        yield ValueError(f'async error code {e.status} on url {error_on} - {rp}')
                    except Exception as e:
                        logger.exception(f'Exception while parsing async response for text {answer_text}')
                        yield e
                else:
                    msg = f'Got an async response which is not exception or ClientResponse. ' \
                          f'This should never happen! response is {raw_answer}'
                    logger.error(msg)
                    yield ValueError(msg)

    def _get(self, endpoint: str, url_params: dict=None, do_basic_auth: bool=None, use_json_in_response: bool = True,
             return_response_raw=False):
        auth_dict = None
        if do_basic_auth:
            auth_dict = (self._username, self._password)

        params = None
        if url_params:
            params = url_params

        headers = self._session_headers

        response = requests.get(
            f'{self._url_base}{endpoint}',
            params=params,
            headers=headers,
            verify=False,
            auth=auth_dict
        )

        response.raise_for_status()

        if use_json_in_response:
            return response.json()
        elif return_response_raw:
            return response
        else:
            return response.content

    def _connect(self):
        # Note that the following self._get will have the application/xml Accept type,
        # but only afterwards we will update session headers to application/json.
        # when having both 'Accept' in permanent and session headers, session wins.
        self._get('system/info', do_basic_auth=True, use_json_in_response=False)
        self._session_headers['Accept'] = 'application/json'

        try:
            self._get('mdm/devices/search', url_params={'pagesize': 1, 'page': 0}, do_basic_auth=True)
        except Exception:
            self._get('mdm/devices/search', url_params={'pagesize': 1, 'page': 1}, do_basic_auth=True)

    @staticmethod
    def _prepare_async_dict(request_dict):
        return {'do_basic_auth': True,
                # Ask to return raw text so we will perform the from_json to mute exception logs
                'return_response_raw': False, 'use_json_in_response': False,
                **request_dict}

    def _parse_subendpoint_async_response(self, response, subendpoint, request_dict) -> Optional[dict]:

        if not self._is_async_response_good(response):
            logger.warning(f'Async response returned bad for request {request_dict}, got: {response}')
            return None

        # Note: We parse json here so we can suppress error logging for optional sub-endpoints
        try:
            response = json.loads(response)
        except Exception:
            # optional subendpoints are not reported on failure
            if subendpoint in ERROR_MUTED_SUBENDPOINTS:
                return None
            logger.exception(f'Invalid response retrieved for request {request_dict}')
            return None

        return response

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals
    def get_device_list(self):
        serials_imei_set = set()

        # get first page of raw devices
        devices_raw_list = []
        page_size = PAGE_SIZE
        try:
            devices_search_raw = self._get(
                'mdm/devices/search', url_params={'pagesize': page_size, 'page': 0}, do_basic_auth=True)
            pages_count = 1
        except Exception:
            devices_search_raw = self._get(
                'mdm/devices/search', url_params={'pagesize': page_size, 'page': 1}, do_basic_auth=True)
            pages_count = 2
        devices_raw_list += (devices_search_raw.get('Devices') or [])

        # retrieve the rest of the raw devices using async requests
        device_raw_requests = []
        total_count = min(devices_search_raw.get('Total', 1), MAX_DEVICES_NUMBER)
        logger.info(f'Got {total_count} devices, but setting to {page_size}')
        total_count = page_size
        while total_count > pages_count * page_size:
            try:
                device_raw_requests.append({
                    'name': 'mdm/devices/search',
                    'url_params': {'pagesize': page_size,
                                   'page': pages_count},
                    'do_basic_auth': True,
                })
            except Exception:
                logger.exception(f'Got problem fetching page {pages_count}')
            pages_count += 1

        # fill up device_raw_list
        for response in self._async_get(device_raw_requests, retry_on_error=True):
            if not self._is_async_response_good(response):
                logger.error(f'Async response returned bad, its {response}')
                continue

            if not isinstance(response, dict):
                logger.warning(f'Invalid response returned: {response}')
                continue

            devices_raw_list += (response.get('Devices') or [])
        logger.info(f'Got {len(devices_raw_list)} Devices')

        # prepare async requests for device info
        device_raw_by_device_id = {}
        async_requests = []
        for device_raw in devices_raw_list:
            try:
                device_id = (device_raw.get('Id') or {}).get('Value') or 0
                if device_id == 0:
                    logger.exception(f'No id for device {device_raw}')
                    continue
            except Exception:
                logger.exception(f'Problem getting id for {device_raw}')
                continue
            device_raw_by_device_id.setdefault(str(device_id), device_raw)
            async_requests.extend(self._prepare_async_dict(request_dict) for request_dict in
                                  [{'name': f'mdm/devices/{str(device_id)}/apps',
                                    # Retrieve apps initial page. if needed, additional pages would be requested later
                                    'url_params': {'pagesize': page_size, 'page': 0}},
                                   {'name': f'mdm/devices/{str(device_id)}/network'},
                                   {'name': f'mdm/devices/{str(device_id)}/notes'},
                                   {'name': f'mdm/devices/{str(device_id)}/tags'},
                                   {'name': f'mdm/devices/{str(device_id)}/profiles'}])
            if device_raw.get('SerialNumber'):
                serials_imei_set.add(device_raw.get('SerialNumber'))
            if device_raw.get('Imei'):
                serials_imei_set.add(device_raw.get('Imei'))

        # run the async requests
        # prepare for additional requests, e.g. apps additional pages
        additional_async_requests = []

        # Note: we zip together responses with their originating request
        for request_dict, response in zip(async_requests, self._async_get(async_requests, retry_on_error=True)):
            try:
                # Note: if this line does not evaluate correctly - it is a serious bug that be caught at except below.
                device_id, response_subendpoint = request_dict.get('name').rstrip('/').rsplit('/', 2)[-2:]
                device_raw = device_raw_by_device_id[device_id]
                # default subendpoint response to None to mark we got its response,
                #   it would be adjusted to the correct value later
                device_raw.setdefault(response_subendpoint, None)
            except Exception:
                logger.warning(f'failed to locate subendpoint for request {request_dict}, response: {response}')
                continue

            response = self._parse_subendpoint_async_response(response, response_subendpoint, request_dict)
            if not response:
                continue

            if not isinstance(response, (dict, list)):
                logger.warning(f'invalid {response_subendpoint} response returned: {response}')
                return None

            if response_subendpoint == 'network':
                device_raw['Network'] = response
                continue

            # the rest of the endpoints require a dict
            if not isinstance(response, dict):
                logger.warning(f'invalid {response_subendpoint} response returned: {response}')
                return None

            if response_subendpoint == 'apps':
                device_raw.setdefault('DeviceApps', []).extend(response.get('DeviceApps') or [])

                # try to append additional pages for later handling
                try:
                    total_count = min(response.get('Total', 1), MAX_APPS_NUMBER)
                    pages_count = 1
                    while total_count > pages_count * page_size:
                        try:
                            additional_async_requests.append(self._prepare_async_dict({
                                'name': f'mdm/devices/{str(device_id)}/apps',
                                'url_params': {'pagesize': page_size, 'page': pages_count}}))
                        except Exception:
                            logger.exception(f'Got problem fetching app for {device_raw} in page {pages_count}')
                        pages_count += 1

                except Exception:
                    logger.exception(f'Problem fetching apps for {device_raw}')

                continue

            elif response_subendpoint == 'notes':
                device_raw['DeviceNotes'] = response.get('DeviceNotes')
                continue

            elif response_subendpoint == 'tags':
                device_raw['DeviceTags'] = response.get('Tag')
                continue

            elif response_subendpoint == 'profiles':
                device_raw['profiles_raw'] = response.get('DeviceProfiles')
                continue

            else:
                logger.error(f'Unknown subendpoint returned "{response_subendpoint}": {response}')
                continue

        # perform the additional apps pages requests
        for request_dict, response in zip(additional_async_requests,
                                          self._async_get(additional_async_requests, retry_on_error=True)):
            try:
                # Note: if this line does not evaluate correctly - it is a serious bug that be caught at except below.
                device_id, response_subendpoint = request_dict.get('name').rstrip('/').rsplit('/', 2)[-2:]
                device_raw = device_raw_by_device_id[device_id]
            except Exception:
                logger.warning(f'failed to locate subendpoint for request {request_dict}, response: {response}')
                continue

            response = self._parse_subendpoint_async_response(response, response_subendpoint, request_dict)
            if not response:
                continue

            if response_subendpoint == 'apps':
                device_raw.setdefault('DeviceApps', []).extend(response.get('DeviceApps') or [])

            else:
                logger.error(f'Unknown subendpoint returned "{response_subendpoint}": {response}')
                continue

        # yield enrolled devices
        for device_raw in device_raw_by_device_id.values():
            yield device_raw, ENROLLED_DEVICE

        self._session_headers['Accept'] = 'application/json;version=2'
        uuid_list = []
        try:
            uuids_raw = self._get('system/groups/search', do_basic_auth=True)['OrganizationGroups']
            for uuid_raw in uuids_raw:
                if uuid_raw.get('Uuid'):
                    uuid_list.append(uuid_raw.get('Uuid'))
        except Exception:
            pass
        try:
            group_devices_requests = [self._prepare_async_dict({'name': f'mdm/dep/groups/{uuid_id}/devices'})
                                      for uuid_id in uuid_list]
            for request_dict, response in zip(group_devices_requests,
                                              self._async_get(group_devices_requests, retry_on_error=True)):

                group_device_raw_list = self._parse_subendpoint_async_response(response, 'group devices', request_dict)
                if not isinstance(group_device_raw_list, list):
                    continue
                logger.info(f'Got {len(group_device_raw_list)} Group devices for request {request_dict}')

                for device_raw in group_device_raw_list:
                    if device_raw.get('deviceImei') and device_raw.get('deviceImei') in serials_imei_set:
                        continue
                    if device_raw.get('deviceSerialNumber')\
                            and device_raw.get('deviceSerialNumber') in serials_imei_set:
                        continue
                    yield device_raw, NOT_ENROLLED_DEVICE
        except Exception:
            logger.exception(f'Problem getting not enrolled devices')


def main():
    try:
        with open(SECRETS_FILE, 'rt') as sf:
            secrets = json.loads(sf.read())
        domain = secrets['domain']
        api_key = secrets['api_key']
        username = secrets['username']
        password = secrets['password']
    except Exception:
        print(f'Please provide the credentials: ')
        domain = input('Domain: ')
        username = input('Username: ')
        password = getpass.getpass('Password: ')
        api_key = getpass.getpass('API Key: ')

    connection = AirwatchConnection(
        domain,
        api_key,
        username,
        password
    )

    with open(SECRETS_FILE, 'wt') as sf:
        sf.write(json.dumps({
            'domain': domain,
            'username': username,
            'password': password,
            'api_key': api_key
        }))

    logger.info(f'Trying to connect...')
    connection._connect()
    logger.info(f'Connection Successful')

    for i, (device, device_type) in enumerate(connection.get_device_list()):
        # print(f'------- DEVICE {i} ---------')
        print(f'Successully got device {i}')
        # print(json.dumps(device, indent=4))

    print(f'Done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
