import json
import logging
from collections import defaultdict
from typing import Optional, Iterable

from axonius.clients.rest.connection import RESTConnection, ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import int_or_none
from infoblox_netmri_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class InfobloxNetmriConnection(RESTConnection):
    """ rest client for InfobloxNetmri adapter """

    def __init__(self, domain: str, *args, verify_ssl=False, **kwargs):
        super().__init__(domain, *args, verify_ssl=verify_ssl,
                         url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._api_version = None

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            body_params = json.dumps({'username': self._username, 'password': self._password})
            self._post(consts.AUTHENTICATION_URL, body_params=body_params, use_json_in_body=False)

            server_info = self._get('server_info')
            if not (isinstance(server_info, dict) and server_info.get('latest_api_version')):
                raise RESTException(f'Can\'t find api version {server_info}')
            self._api_version = server_info.get('latest_api_version')

            self._post(consts.DEVICES_URL.format(api_version=self._api_version), body_params=json.dumps({'limit': 1}),
                       use_json_in_body=False)
        except Exception as e:
            logger.exception(f'Error connecting to NetMRI server: {str(e)}')
            raise RESTException(f'Error: Invalid response from server, please check domain or credentials.'
                                f' The error was: {str(e)}')

    def _get_total(self, api_endpoint, params):
        logger.info(f'Attempting to fetch result count for api endpoint {api_endpoint}')
        params = params or {}
        try:
            total = self._post(f'{self._api_version}/{api_endpoint}', body_params=json.dumps({**params, 'limit': 1}),
                               use_json_in_body=False).get('total')
            if not isinstance(total, int):
                raise ValueError(f'Unexpected value for total: {total}')
        except Exception:
            message = f'Failed to get total count of results for {api_endpoint}'
            logger.exception(message)
            raise
        logger.info(f'Expecting total of {total} results, max is {consts.MAX_NUMBER_OF_DEVICES}')
        return min(total, consts.MAX_NUMBER_OF_DEVICES)

    def _get_vlans_by_device_id(self,
                                params: Optional[dict] = None,
                                limit: int = consts.DEVICE_PER_PAGE,
                                async_chunks: int = ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE):
        params = params or {}
        vlans_by_device_id = defaultdict(list)
        try:
            total_vlans = self._get_total('vlan_members/index', params)
        except Exception as e:
            logger.warning(f'Failed to fetch total result count for vlans!')
            return vlans_by_device_id
        try:
            requests = [{'name': f'{self._api_version}/vlan_members/index',
                         'body_params': json.dumps({**params, 'limit': limit, 'start': i * limit}),
                         'use_json_in_body': False}
                        for i in range(int(total_vlans / limit) + 1)]

            for request, response in zip(requests, self._async_post(requests, chunks=async_chunks, copy_cookies=True)):
                if not self._is_async_response_good(response):
                    logger.warning(f'Bad response returned from request {request}: {response}')
                    continue
                if not (isinstance(response, dict) and isinstance(response.get('vlan_members'), list)):
                    logger.warning(f'Vlan response is not in the correct format {response}')
                    continue
                for vlan in response.get('vlan_members'):
                    if not (isinstance(vlan, dict) and
                            vlan.get('DeviceID')):
                        continue
                    vlans_by_device_id[vlan.get('DeviceID')].append(vlan)
        except Exception as e:
            logger.error(f'Failed to get vlans for devices. Error: {str(e)}')
        return vlans_by_device_id

    def _paginated_get(self,
                       api_endpoint,
                       result_param: str = 'devices',
                       limit: Optional[int] = None,
                       params: Optional[dict] = None,
                       async_chunks: int = ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE) -> Iterable[dict]:
        limit = min(limit or consts.DEVICE_PER_PAGE, consts.DEVICE_PER_PAGE)
        params = params or {}
        try:
            total = self._get_total(api_endpoint, params)
        except Exception as e:
            message = f'Failed to fetch total result count for request "{api_endpoint}"!'
            logger.exception(message)
            raise RESTException(f'{message} Error: {str(e)}')

        vlans_by_device_id = self._get_vlans_by_device_id(params, limit=limit, async_chunks=async_chunks)

        count_so_far = 0
        logger.info(f'Starting to fetch {total} results for {api_endpoint}.')

        requests = [{'name': f'{self._api_version}/{api_endpoint}',
                     'body_params': json.dumps({**params, 'limit': limit, 'start': i * limit}),
                     'use_json_in_body': False}
                    for i in range(int(total / limit) + 1)]

        for request, response in zip(requests, self._async_post(requests, chunks=async_chunks, copy_cookies=True)):
            if not self._is_async_response_good(response):
                logger.warning(f'Bad response returned from request {request}: {response}')
                continue
            this_page = int_or_none(response.get('current')) or 0
            results = response.get(result_param)
            if isinstance(results, list):
                for result in results:
                    result['extra_vlans'] = vlans_by_device_id.get(result.get('DeviceID'))
                    yield result
            elif isinstance(results, dict):
                results['extra_vlans'] = vlans_by_device_id.get(results.get('DeviceID'))
                yield results
            else:
                logger.error(f'Got bad results: {results}')
                continue

            count_so_far += this_page
            if not this_page:
                logger.info(f'Got 0 results after {count_so_far}, out of total {total}')
                break
        logger.info(f'Finished fetching results for {api_endpoint}, yielded {count_so_far} out of {total} results.')

    def _paginated_device_get(self, async_chunks: Optional[int] = None):
        try:
            yield from self._paginated_get('devices/index', async_chunks=async_chunks)
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    # pylint: disable=arguments-differ
    def get_device_list(self, async_chunks: int = ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE):
        try:
            yield from self._paginated_device_get(async_chunks=async_chunks)
        except RESTException as err:
            logger.exception(str(err))
            raise
