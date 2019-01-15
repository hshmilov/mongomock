import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class SaltstackConnection(RESTConnection):
    """ rest client for Saltstack adapter """

    def __init__(self, *args, eauth, **kwargs):
        super().__init__(*args, url_base_prefix='', headers={'Content-Type': 'application/json',
                                                             'Accept': 'application/json'}, **kwargs)
        self._eauth = eauth

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('login',
                              body_params={'username': self._username,
                                           'password': self._password,
                                           'eauth': self._eauth})
        token = None
        ret_value = response.get('return')
        if isinstance(ret_value, dict):
            token = ret_value.get('token')
        elif isinstance(ret_value, list) and isinstance(ret_value[0], dict):
            token = ret_value[0].get('token')
        if not token:
            logger.error(f'Response: {response}')
            raise RESTException(f'Got response with no token: {response}')
        self._session_headers['X-Auth-Token'] = token

    def get_device_list(self):
        for nodes_dict in self._get('minions')['return']:
            try:
                for node_name, node_data in nodes_dict.items():
                    yield node_name, node_data
            except Exception:
                logger.exception(f'Problem in nodes dict')
