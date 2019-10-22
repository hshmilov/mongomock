import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from airwave_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, CLIENT_TYPE, AP_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


class AirwaveConnection(RESTConnection):
    """ rest client for Airwave adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        destination = '/'
        next_action = ''
        params = {'credential_0': self._username,
                  'credential_1': self._password,
                  'login': 'Log In',
                  'destination': destination,
                  'next_action': next_action}
        self._post('LOGIN', url_params=params, use_json_in_response=False)
        self._get('api/list_view.json', url_params={'list': 'client_all', 'fv_id': '0', 'page_length': DEVICE_PER_PAGE})

    def _get_api_endpoint(self, api_endpoint):
        response = self._get('api/list_view.json',
                             url_params={'list': api_endpoint,
                                         'fv_id': '0',
                                         'page_length': DEVICE_PER_PAGE})
        yield from response.get('records')
        total_count = self._get('api/total_count.json',
                                url_params={'list': api_endpoint,
                                            'fv_id': '0'}
                                ).get('total_count')
        total_count = int(total_count)
        logger.info(f'Total Count of {api_endpoint} is {total_count}')
        offset = DEVICE_PER_PAGE
        while offset < min(total_count, MAX_NUMBER_OF_DEVICES) and response.get('has_next') is True:
            try:
                logger.debug(f'Offset is {offset}')
                response = self._get('api/list_view.json',
                                     url_params={'list': api_endpoint,
                                                 'fv_id': '0',
                                                 'page_length': DEVICE_PER_PAGE,
                                                 'start_row': offset})
                yield from response.get('records')
                if len(response.get('records')) < DEVICE_PER_PAGE:
                    break
            except Exception:
                logger.exception(f'Problem with offset {offset}')
            offset += DEVICE_PER_PAGE

    def get_device_list(self):
        for device_raw in self._get_api_endpoint('ap_list'):
            yield device_raw, AP_TYPE

        for device_raw in self._get_api_endpoint('client_all'):
            yield device_raw, CLIENT_TYPE
