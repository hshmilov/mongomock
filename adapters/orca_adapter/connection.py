import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class OrcaConnection(RESTConnection):
    """ rest client for Orca adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        response = self._post('user/session', body_params={'security_token': self._apikey})
        if not response.get('jwt') or not response['jwt'].get('access'):
            raise RESTException(f'Bad response: {response}')
        self._token = response['jwt']['access']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        response = self._get(f'query/assets')
        if not isinstance(response, dict) or not isinstance(response.get('data'), list):
            raise RESTException(f'Bad response: {response}')

    def get_device_list(self):
        devices_alerst_dict = dict()
        try:
            for alert_raw in self._get_api_endpoint('query/alerts'):
                asset_id = alert_raw.get('asset_unique_id')
                if not asset_id:
                    continue
                if asset_id not in devices_alerst_dict:
                    devices_alerst_dict[asset_id] = []
                devices_alerst_dict[asset_id].append(alert_raw)
        except Exception:
            logger.exception(f'Problem with alerts')
        for device_raw in self._get_api_endpoint('query/assets'):
            yield device_raw, devices_alerst_dict

    def _get_api_endpoint(self, endpoint):
        response = self._get(endpoint)
        yield from response['data']
        while response.get('next_page_token'):
            try:
                response = self._get(endpoint, url_params={'next_page_token': response.get('next_page_token')})
                yield from response['data']
            except Exception:
                logger.exception(f'Exception in orca fetch')
                break
