import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from mobi_control_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class MobiControlConnection(RESTConnection):
    """ rest client for MobiControl adapter """

    def __init__(self, *args, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='/MobiControl/api',
                         headers={'Accept': 'application/json'},
                         **kwargs)
        self._client_id = client_id
        self._client_secret = client_secret

    def _connect(self):
        grant_type = f'grant_type=password&username={self._username}&password={self._password}'
        self._session_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        response = self._post('token', body_params=grant_type,
                              use_json_in_body=False,
                              do_basic_auth=True,
                              alternative_auth_dict=(self._client_id, self._client_secret))
        if 'access_token' not in response:
            raise RESTException(f'Bad login got response: {response.content[:100]}')
        self._session_headers['Authorization'] = 'Bearer ' + response['access_token']

    def get_device_list(self):
        skip = 0
        while skip < MAX_NUMBER_OF_DEVICES:
            try:
                devices = self._get('devices/search',
                                    url_params={'skip': skip,
                                                'take': DEVICE_PER_PAGE,
                                                'includeSubgroups': 'true',
                                                'path': '/'})
                if not devices:
                    break
                yield devices
                skip += DEVICE_PER_PAGE

            except Exception:
                logger.exception(f'Problem at offset {skip}')
                break
