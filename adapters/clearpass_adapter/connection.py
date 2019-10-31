import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from clearpass_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES
logger = logging.getLogger(f'axonius.{__name__}')


class ClearpassConnection(RESTConnection):
    """ rest client for Clearpass adapter """

    def __init__(self, *args, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='api', headers={'Content-Type': 'application/json',
                                                                'Accept': 'application/json'}, **kwargs)
        self._client_id = client_id
        self._client_secret = client_secret

    def _connect(self):
        if not self._client_id or not self._client_secret:
            raise RESTException('No client id or secret')
        response = self._post('oauth', body_params={'grant_type': 'client_credentials',
                                                    'client_id': self._client_id,
                                                    'client_secret': self._client_secret
                                                    })
        if 'access_token' not in response:
            logger.exception(f'Bad login. Got this response {response}')
            raise RESTException('Bad login Credentials')
        token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {token}'
        self._get('endpoint', url_params={'calculate_count': 'true', 'offset': 0, 'limit': DEVICE_PER_PAGE})

    # pylint: disable=arguments-differ
    def get_device_list(self, get_extended_info):
        yield from self._get_device_list_from_api('endpoint', 'endpoint', get_extended_info=get_extended_info)
        try:
            yield from self._get_device_list_from_api('network-device', 'network-device', get_extended_info=False)
        except Exception:
            logger.exception('Problem getting networks')

    def _get_extra_data_and_yield_devices(self, devices_raw, get_extended_info, device_type):
        if get_extended_info:
            try:
                async_requests = []
                for device_raw in devices_raw:
                    mac = device_raw.get('mac_address')
                    async_requests.append({'name': f'insight/endpoint/mac/{mac}'})
                for i, async_response in enumerate(self._async_get(async_requests, chunks=100)):
                    if self._is_async_response_good(async_response):
                        devices_raw[i]['extended_info'] = async_response
            except Exception:
                logger.debug(f'Problem getting extended info for')

        for device_raw in devices_raw:
            yield device_raw, device_type

    def _get_device_list_from_api(self, api_name, device_type, get_extended_info):
        response = self._get(api_name, url_params={'calculate_count': 'true',
                                                   'offset': 0, 'limit': DEVICE_PER_PAGE})
        devices_raw = response['_embedded']['items']
        yield from self._get_extra_data_and_yield_devices(devices_raw, get_extended_info, device_type)
        count = response['count']
        if count >= MAX_NUMBER_OF_DEVICES:
            logger.error(f'Error, count - {count} is larger than MAX_NUMBER_OF_DEVICES '
                         f'- {MAX_NUMBER_OF_DEVICES}, skipping over pages!')
        offset = DEVICE_PER_PAGE
        # pylint: disable=R1702
        while offset < min(count, MAX_NUMBER_OF_DEVICES):
            if offset % (DEVICE_PER_PAGE * 10) == 0:
                logger.info(f'Got to offset {offset} out of count {count}')
            try:
                response = self._get(api_name, url_params={'calculate_count': 'false',
                                                           'offset': offset, 'limit': DEVICE_PER_PAGE})
                devices_raw = response['_embedded']['items']
                if not devices_raw:
                    break
                yield from self._get_extra_data_and_yield_devices(devices_raw, get_extended_info, device_type)
            except Exception:
                logger.exception(f'Problem fetching offset {offset}')
                break
            offset += DEVICE_PER_PAGE
