import logging

from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class RedsealConnection(RESTConnection):
    """ rest client for redseal adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        self._session_headers['x-csrf-token'] = 'Fetch'
        response = self._get('api/v2/groups/**', url_params={'recursiveMetrics': 'false'}, return_response_raw=True,
                             use_json_in_response=False,
                             do_basic_auth=True)
        self._session_headers['x-csrf-token'] = response.headers['x-csrf-token']

    def get_device_list(self):
        pass

    def get_urls(self):
        response = self._get('api/v2/groups/**/members',
                             url_params={'kinds': 'computer_system',
                                         'pageSize': '100',
                                         'recursive': 'true'})
        items = response['items']
        while response.get('nextPageToken'):
            page_token = response.get('nextPageToken')
            response = self._get('api/v2/groups/**/members',
                                 url_params={'kinds': 'computer_system',
                                             'pageSize': '100',
                                             'recursive': 'true',
                                             'pageToken': page_token})
            items.extend(response['items'])
        for item in items:
            device_id = item.get('id')
            if item.get('kind') and item.get('kind').startswith('computer_system#device'):
                yield self._get_url_request(f'data/device/{device_id}')
            elif item.get('kind') and item.get('kind').startswith('computer_system#host'):
                yield self._get_url_request(f'data/host/{device_id}')
