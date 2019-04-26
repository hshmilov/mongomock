import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from saltstack_enterprise_adapter.consts import MAX_PAGES, DEVICES_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class SaltstackEnterpriseConnection(RESTConnection):
    """ rest client for SaltstackEnterprise adapter """

    def __init__(self, *args, config_name, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._config_name = config_name

    def _connect(self):
        if not self._username or not self._password or not self._config_name:
            raise RESTException('No username or password or config_name')

        params = {
            'username': self._username,
            'password': self._password,
            'config_name': self._config_name,
        }

        response = self._get('account/login', return_response_raw=True, use_json_in_response=False)
        self._session_headers['X-Xsrftoken'] = response.headers['X-Xsrftoken']
        self._post('account/login', body_params=params)

    def get_device_list(self):
        for index in range(0, MAX_PAGES):
            results = self.get_page(index)
            yield from results
            if len(results) < DEVICES_PER_PAGE:
                return

    def get_page(self, index):
        params = {
            'resource': 'minions',
            'method': 'get_minion_details',
            'kwarg': {
                'page': index,
                'reverse': False,
                'limit': DEVICES_PER_PAGE
            }
        }
        try:
            json_results = self._post('rpc', body_params=params)
            if not json_results.get('ret') or not json_results['ret'].get('results'):
                logger.error(f'Failed to fetch page number {index}. Missing results: {json_results}')
                return []

            return json_results['ret']['results']
        except Exception as e:
            logger.exception(f'Failed to fetch page number {index}')
            return []
