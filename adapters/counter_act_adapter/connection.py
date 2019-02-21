import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class CounterActConnection(RESTConnection):
    """ rest client for CounterAct adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/hal+json'},
                         **kwargs)

    def _refresh_token(self):
        auth_data = f'username={self._username}&password={self._password}'
        self._session_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        response = self._post('login',
                              use_json_in_body=False,
                              body_params=auth_data,
                              use_json_in_response=False).decode('utf-8')
        self._session_headers['Authorization'] = response

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._refresh_token()

    def get_device_list(self):
        self._refresh_token()
        self._session_headers['Accept'] = 'application/hal+json'
        devices_raw = self._get('hosts')['hosts']
        for device_raw in devices_raw:
            try:
                self._refresh_token()
                href = device_raw.get('_links').get('self').get('href')
                device_raw['extra'] = self._get(href, force_full_url=True)
            except Exception:
                logger.exception(f'Problem get more data for {device_raw}')
            yield device_raw
