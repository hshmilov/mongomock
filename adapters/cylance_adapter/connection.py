import datetime
import logging
import uuid

import jwt

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cylance_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class CylanceConnection(RESTConnection):
    def __init__(self, *args, app_id: str = '', tid: str = '', app_secret: str = '', **kwargs):
        """ Initializes a connection to Cylance using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Cylance
        """
        super().__init__(*args, **kwargs)
        self._app_id = app_id
        self._app_secret = app_secret
        self._tid = tid
        self._tokens = {}

    def _create_token_for_scopre(self, scope):
        if self._tid is not None and self._app_id is not None and self._app_secret is not None:
            int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds())
            epoch_time = int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds())
            epoch_timeout = epoch_time + 60 * consts.NUMBER_OF_MINUTES_UNTIL_TOKEN_TIMEOUT
            claims = {'exp': epoch_timeout, 'iat': epoch_time, 'iss': 'http://cylance.com', 'sub': self._app_id,
                      'tid': self._tid, 'jti': str(uuid.uuid4()), 'scp': scope}
            auth_token_encoded = jwt.encode(claims, self._app_secret, algorithm='HS256').decode('utf-8')
            response = self._post('auth/v2/token', body_params={'auth_token': auth_token_encoded})
            if 'access_token' not in response:
                raise RESTException(f'Couldnt get token from response {response}')
            self._tokens[scope] = response['access_token']
        else:
            raise RESTException('No tid or app secrer or app id')

    def _connect(self):
        """ Connects to the service """
        self._create_token_for_scopre('device:list')

    def _get_ids_bulks(self):
        page_num = 1
        self._session_headers['Authorization'] = 'Bearer ' + self._tokens['device:list']
        devices_response_raw = self._get(
            'devices/v2', url_params={'page_size': consts.DEVICE_PER_PAGE, 'page': str(page_num)})
        yield [basic_device.get('id') for basic_device in devices_response_raw.get('page_items', [])]
        total_pages = devices_response_raw.get('total_pages', 0)  # Waiting to know to right fields
        first_try_to_refresh = True
        while page_num < total_pages:
            try:
                page_num += 1
                if page_num % 100 == 0:
                    self._create_token_for_scopre('device:list')
                self._session_headers['Authorization'] = 'Bearer ' + self._tokens['device:list']
                yield [basic_device.get('id') for basic_device in
                       self._get('devices/v2', url_params={'page_size': consts.DEVICE_PER_PAGE,
                                                           'page': str(page_num)}).get('page_items', [])]
            except Exception as e:
                if first_try_to_refresh and '401' in str(e):
                    self._create_token_for_scopre('device:list')
                    first_try_to_refresh = False
                    page_num -= 1
                logger.exception(f'Problem fetching page number {str(page_num)}')

    def get_device_list(self):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Cylance's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        # Now use asyncio to get all of these requests
        for bulk_number, bulk_ids in enumerate(self._get_ids_bulks()):
            # We must refresh the token sometimes so we won't get to token timeout
            if bulk_number % 50 == 0:
                self._create_token_for_scopre('device:read')
            async_requests = []
            for device_id in bulk_ids:
                try:
                    if not device_id:
                        logger.warning(f'Bad device')
                        continue
                    async_requests.append({'name': f'devices/v2/{device_id}'})
                except Exception:
                    logger.exception(f'Got problem with id {device_id}')
            self._session_headers['Authorization'] = 'Bearer ' + self._tokens['device:read']
            yield from self._async_get_only_good_response(async_requests)
