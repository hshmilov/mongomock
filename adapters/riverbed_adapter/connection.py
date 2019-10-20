import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class RiverbedConnection(RESTConnection):
    """ rest client for Riverbed adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if (not self._username or not self._password) and not self._apikey:
            raise RESTException('No username or password')
        if not self._apikey:
            response = self._post('mgmt.aaa/1.0/token',
                                  body_params={'user_credentials': {'username': self._username,
                                                                    'password': self._password},
                                               'generate_refresh_token': False})
            if 'access_token' not in response:
                raise RESTException(f'Bad response: {response}')
            self._token = response['access_token']
        else:
            self._token = self._apikey
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._get('cmc.appliance_inventory/1.2/appliances')

    def get_device_list(self):
        yield from self._get('cmc.appliance_inventory/1.2/appliances')
