import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from symantec_cloud_workload_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecCloudWorkloadConnection(RESTConnection):
    """ rest client for SymantecCloudWorkload adapter """

    def __init__(self, *args, domain_id, customer_id, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='dcs-service/dcscloud/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._domain_id = domain_id
        self._customer_id = customer_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._permanent_headers['x-epmp-customer-id'] = self._customer_id
        self._permanent_headers['x-epmp-domain-id'] = self._domain_id

    def _connect(self):
        if not self._domain_id or not self._customer_id or not self._client_id or not self._client_secret:
            raise RESTException('Missing Critical Parameter')
        response = self._post('oauth/tokens',
                              body_params={'client_id': self._client_id,
                                           'client_secret': self._client_secret})
        self._token = response.get('access_token')
        self._token_type = response.get('token_type')
        if not self._token or not self._token_type:
            raise RESTException(f'Response without token: {response}')
        self._session_headers['Authorization'] = f'{self._token_type} {self._token}'
        self._post('ui/assets',
                   body_params={'limit': DEVICE_PER_PAGE,
                                'offset': 0,
                                'include': 'installed_products'})

    def get_device_list(self):
        offset = 0
        response = self._post('ui/assets',
                              body_params={'limit': DEVICE_PER_PAGE,
                                           'offset': offset,
                                           'include': 'installed_products'})
        yield from response['results']
        offset += 1
        count = response['count']
        while offset * DEVICE_PER_PAGE < min(count, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._post('ui/assets',
                                      body_params={'limit': DEVICE_PER_PAGE,
                                                   'offset': offset,
                                                   'include': 'installed_products'})
                if not response.get('results'):
                    break
                yield from response['results']
                offset += 1
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                break
