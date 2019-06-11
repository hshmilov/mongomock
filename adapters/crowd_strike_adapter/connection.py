import time
import logging

from datetime import datetime, timedelta

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from crowd_strike_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')

# XXX: For some reason this file doesn't ignore logging-fstring-interpolation
# although we got it in pylintrc ignore. add disable for it, and disable the disable warning
# pylint: disable=I0021
# pylint: disable=W1203


# pylint: disable=too-many-statements
class CrowdStrikeConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, headers={'Accept': 'application/json'})
        self.last_token_fetch = None

    def refresh_access_token(self, force=False):
        if not self.last_token_fetch or (self.last_token_fetch + timedelta(minutes=20) < datetime.now()) or force:
            response = self._post('oauth2/token', use_json_in_body=False,
                                  body_params={'client_id': self._username,
                                               'client_secret': self._password})
            token = response['access_token']
            self._session_headers['Authorization'] = f'Bearer {token}'
            self.last_token_fetch = datetime.now()

    def _connect(self):
        if not self._username or not self._password is not None:
            raise RESTException('No user name or API key')
        try:
            self.refresh_access_token(force=True)  # just try
            self._got_token = True
            logger.info('oauth success')
        except Exception:
            logger.exception('Oauth failed')
            self._got_token = False
        self._get('devices/queries/devices/v1',
                  do_basic_auth=not self._got_token,
                  url_params={'limit': consts.DEVICES_PER_PAGE, 'offset': 0})

    # pylint: disable=arguments-differ
    def get_device_list(self, async_chunk_size):
        # pylint: disable=R0912
        ids_list = []
        offset = 0
        response = self._get('devices/queries/devices/v1',
                             url_params={'limit': consts.DEVICES_PER_PAGE, 'offset': offset},
                             do_basic_auth=not self._got_token)
        try:
            ids_list.extend(response['resources'])
        except Exception:
            logger.exception(f'Problem getting resource')
            raise RESTException('Cant get resources')
        try:
            total_count = response['meta']['pagination']['total']
        except Exception:
            logger.exception(f'Cant get total count')
            raise RESTException('Cant get total count')
        offset += consts.DEVICES_PER_PAGE
        while offset < total_count and offset < consts.MAX_NUMBER_OF_DEVICES:
            try:
                ids_list.extend(self._get('devices/queries/devices/v1',
                                          url_params={'limit': consts.DEVICES_PER_PAGE,
                                                      'offset': offset},
                                          do_basic_auth=not self._got_token)['resources'])
                if self._got_token:
                    self.refresh_access_token()
            except Exception:
                logger.exception(f'Problem getting offset {offset}')
            offset += consts.DEVICES_PER_PAGE

        # Now use asyncio to get all of these requests
        async_requests = []
        for device_id in ids_list:
            try:
                if device_id is None or device_id == '':
                    logger.warning(f'Bad device {device_id}')
                    continue
                async_requests.append({'name': f'devices/entities/devices/v1?ids={device_id}',
                                       'do_basic_auth': not self._got_token})
            except Exception:
                logger.exception(f'Got problem with id {device_id}')
        if len(async_requests) < 480:
            for response in self._async_get_only_good_response(async_requests):
                try:
                    yield response['resources'][0]
                    if self._got_token:
                        self.refresh_access_token()
                except Exception:
                    logger.exception(f'Problem getting async response {str(response)}')
        async_requests_first = async_requests[:480]
        async_requests = async_requests[480:]
        for response in self._async_get_only_good_response(async_requests_first, chunks=async_chunk_size):
            try:
                yield response['resources'][0]
                if self._got_token:
                    self.refresh_access_token()
            except Exception:
                logger.exception(f'Problem getting async response {str(response)}')
        time.sleep(5)
        while async_requests:
            async_requests_first = async_requests[:500]
            for response in self._async_get_only_good_response(async_requests_first, chunks=async_chunk_size):
                try:
                    yield response['resources'][0]
                    if self._got_token:
                        self.refresh_access_token()
                except Exception:
                    logger.exception(f'Problem getting async response {str(response)}')
            time.sleep(5)
            async_requests = async_requests[500:]
