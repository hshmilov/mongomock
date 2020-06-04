import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from upguard_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class UpguardConnection(RESTConnection):
    """ rest client for Upguard adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/public',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._permanent_headers['Authorization'] = self._apikey
        self._get('breaches', url_params={'page_size': DEVICE_PER_PAGE})

    def get_user_list(self):
        response = self._get('breaches', url_params={'page_size': DEVICE_PER_PAGE})
        breached_identities = response['breached_identities']
        breaches = response['breaches']
        page = 1
        while response.get('next_page_token') and page * DEVICE_PER_PAGE < MAX_NUMBER_OF_DEVICES:
            try:
                page_token = response.get('next_page_token')
                response = self._get('breaches', url_params={'page_size': DEVICE_PER_PAGE,
                                                             'page_token': page_token})
                breached_identities.extend(response['breached_identities'])
                breaches.extend(response['breaches'])
                page += 1
            except Exception:
                logger.exception(f'Problem in fetch break')
        breaches_id_dict = dict()
        for breach_raw in breaches:
            try:
                breach_id = breach_raw['id']
                breaches_id_dict[breach_id] = breach_raw
            except Exception:
                logger.exception(f'Problem with breach {breach_raw}')
        return breached_identities, breaches_id_dict

    def get_device_list(self):
        pass
