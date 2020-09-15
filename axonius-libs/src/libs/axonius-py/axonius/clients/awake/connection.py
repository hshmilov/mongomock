import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class AwakeConnection(RESTConnection):
    """ rest client for Awake adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='awakeapi/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        response = self._post('authtoken', body_params={'loginUsername': self._username,
                                                        'loginPassword': self._password})
        self._token = (response.get('token') or {}).get('value')
        self._session_headers['authentication'] = f'access {self._token}'

    def get_device_list(self):
        start_time = str(datetime.datetime.utcnow()).split(' ')[0] + 'T00:00:00Z'
        end_time = str(datetime.datetime.utcnow() + datetime.timedelta(days=1)).split(' ')[0] + 'T00:00:00Z'
        body_params = {'queryExpression': '', 'startTime': start_time, 'endTime': end_time}
        yield from self._post('query/devices', body_params=body_params)
        start_time = str(datetime.datetime.utcnow() - datetime.timedelta(days=1)).split(' ')[0] + 'T00:00:00Z'
        end_time = str(datetime.datetime.utcnow()).split(' ')[0] + 'T00:00:00Z'
        body_params = {'queryExpression': '', 'startTime': start_time, 'endTime': end_time}
        yield from self._post('query/devices', body_params=body_params)
        for day in range(1, 30):
            start_time = str(datetime.datetime.utcnow() - datetime.timedelta(days=1 + day)).split(' ')[0] + 'T00:00:00Z'
            end_time = str(datetime.datetime.utcnow() - datetime.timedelta(days=day)).split(' ')[0] + 'T00:00:00Z'
            body_params = {'queryExpression': '', 'startTime': start_time, 'endTime': end_time}
            yield from self._post('query/devices', body_params=body_params)
