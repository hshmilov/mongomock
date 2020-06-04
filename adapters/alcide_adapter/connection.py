import time
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class AlcideConnection(RESTConnection):
    """ rest client for Alcide adapter """

    def __init__(self, *args, org, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._org = org

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('login', body_params={'org': self._org,
                                                    'username': self._username,
                                                    'password': self._password})
        if not isinstance(response, dict) or not response.get('token'):
            logger.error(f'Response was: {response}')
            raise RESTException(f'Bad response from server')
        self._session_headers['Authorization'] = response['token']

    def get_device_list(self):
        entities_time = int(time.time() * 1000)
        body_params = {'query': '{entities (time: '
                                f'{entities_time}'
                                ') '
                                '{ id uid name namespace monitorTime monitorActive agentTime '
                                'agentActive datacenter cluster label metaType metadata '
                                '{key value} metadataLabels '
                                '{key value}   ipAddresses {addressSpace address} isAppComponent}}'}
        yield from self._post('graphql', body_params=body_params)['data']['entities']
