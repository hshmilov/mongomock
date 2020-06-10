import datetime
import logging
import urllib.parse

from typing import List

import funcy

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from symantec_ccs_adapter.consts import DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')
ASYNC_CHUNKS = 50


class SymantecCcsConnection(RESTConnection):
    """ rest client for SymantecCcs adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='ccs/api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._last_refresh = None
        self._expires_in = None

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return

        password = urllib.parse.quote(self._password)
        response = self._post('oauth/tokens',
                              use_json_in_body=False,
                              body_params=f'grant_type=password&username={self._username}&password={password}')
        if not response.get('access_token'):
            raise RESTException(f'Bad login response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(int(response['expires_in']) / 2)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._last_refresh = None
        self._refresh_token()
        response = self._get('Assets',
                             url_params={'pagesize': 1,
                                         'page': 0,
                                         'ContainerPath': 'asset system',
                                         'SearchSubTree': True,
                                         'attributes': '(displayName = *)'})
        if not response.get('assetDataList'):
            raise RESTException(f'Bad response from server')

    def _get_device_ids(self):
        page = 0
        response = self._get('Assets',
                             url_params={'pagesize': DEVICE_PER_PAGE,
                                         'page': page,
                                         'ContainerPath': 'asset system',
                                         'SearchSubTree': True,
                                         'attributes': '(displayName = *)'})
        if not response.get('assetDataList'):
            raise RESTException(f'Bad response from server')
        for device_raw in response.get('assetDataList'):
            if device_raw.get('Id'):
                yield device_raw.get('Id')
        total_pages = response.get('TotalPages')
        if not isinstance(total_pages, int):
            return
        page = 1
        while page < total_pages:
            try:
                response = self._get('Assets',
                                     url_params={'pagesize': DEVICE_PER_PAGE,
                                                 'page': page,
                                                 'ContainerPath': 'asset system',
                                                 'SearchSubTree': True,
                                                 'attributes': '(displayName = *)'})
                if not response.get('assetDataList'):
                    raise RESTException(f'Bad response from server')
                for device_raw in response.get('assetDataList'):
                    if device_raw.get('Id'):
                        yield device_raw.get('Id')
                page += 1
            except Exception:
                logger.exception(f'Problem with page {page}')
                break

    # pylint: disable=arguments-differ, too-many-nested-blocks
    def get_device_list(self, evaluation_checks: List[str] = None):
        self._refresh_token()
        total_devices = 0
        for device_ids in funcy.chunks(ASYNC_CHUNKS, self._get_device_ids()):
            total_devices += ASYNC_CHUNKS
            if total_devices % (ASYNC_CHUNKS * 5) == 0:
                logger.info(f'Got {total_devices} by now')
            try:
                async_requests = [{'name': f'Assets/{device_id}'} for device_id in device_ids]
                devices = {
                    device['ID']: device
                    for device in self._async_get_only_good_response(async_requests, chunks=ASYNC_CHUNKS)
                }
                self._refresh_token()
                async_requests = []
                for device_id in devices.keys():
                    for check in (evaluation_checks or []):
                        async_requests.append(
                            {
                                'name': 'Results',
                                'body_params': {'AssetID': device_id, 'StandardID': check}
                            }
                        )

                for async_request, check_response in zip(async_requests, self._async_post(async_requests)):
                    if self._is_async_response_good(check_response):
                        device_id = async_request['body_params']['AssetID']
                        standard_id = async_request['body_params']['StandardID']

                        if 'standards' not in devices[device_id]:
                            devices[device_id]['standards'] = {}
                        devices[device_id]['standards'][standard_id] = check_response
                    else:
                        logger.debug(f'Got a bad async response: {check_response}')

                yield from devices.values()

            except Exception:
                logger.exception(f'Problem getting data for {str(device_ids)}')
            finally:
                self._refresh_token()
