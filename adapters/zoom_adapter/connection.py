import time
import logging
import jwt

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from zoom_adapter.consts import USER_PER_PAGE, MAX_NUMBER_OF_USERS

logger = logging.getLogger(f'axonius.{__name__}')


class ZoomConnection(RESTConnection):
    """ rest client for Zoom adapter """

    def __init__(self, *args, api_secret, **kwargs):
        super().__init__(*args, url_base_prefix='v2',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._api_secret = api_secret

    def _refresh_token(self):
        exp = (time.time() + 7200) * 1000
        algorithm = 'HS256'
        payload = {'iss': self._apikey,
                   'exp': exp}
        token = jwt.encode(payload, self._api_secret, algorithm=algorithm).decode('utf-8')
        self._session_headers['Authorization'] = f'Bearer {token}'

    def _connect(self):
        if not self._apikey or not self._api_secret:
            raise RESTException('No API Key or Secret Key')
        self._refresh_token()
        self._get('users', url_params={'page_size': USER_PER_PAGE, 'page_number': 1})

    def _get_api_endpoint(self, endpoint):
        page_number = 1
        response = self._get(endpoint, url_params={'page_size': USER_PER_PAGE, 'page_number': page_number})
        yield from response[endpoint.split('/')[-1]]
        if response.get('total_records'):
            try:
                total_records = int(response.get('total_records'))
                while page_number * USER_PER_PAGE < min(total_records, MAX_NUMBER_OF_USERS):
                    page_number += 1
                    response = self._get(endpoint, url_params={'page_size': USER_PER_PAGE, 'page_number': page_number})
                    yield from response[endpoint.split('/')[-1]]
            except Exception:
                logger.exception(f'Problem with endpoint {endpoint}')

    def get_device_list(self):
        try:
            yield from self._get_api_endpoint('h323/devices')
        except Exception:
            logger.info('Problem with devices', exc_info=True)

    def get_user_list(self):
        groups_dict = dict()
        try:
            for group_raw in self._get_api_endpoint('groups'):
                groups_dict[group_raw.get('id')] = group_raw
        except Exception:
            logger.info('Problem with groups', exc_info=True)
        im_groups_dict = dict()
        try:
            for im_group_raw in self._get_api_endpoint('im/groups'):
                im_groups_dict[im_group_raw.get('id')] = im_group_raw
        except Exception:
            logger.info('Problem with devices', exc_info=True)
        for user_raw in self._get_api_endpoint('users'):
            yield user_raw, groups_dict, im_groups_dict
