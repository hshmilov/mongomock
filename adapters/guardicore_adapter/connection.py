import time
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from guardicore_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class GuardicoreConnection(RESTConnection):
    """ rest client for Guardicore adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v3.0',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('authenticate',
                              body_params={'username': self._username,
                                           'password': self._password})
        if not response.get('access_token'):
            raise RESTException(f'Bad login response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._get('assets', url_params={'limit': DEVICE_PER_PAGE, 'offset': 0}).get('objects')

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def get_device_list(self):
        incidents_dict = dict()
        try:
            for incident_raw in self._get_api_endpoint('incidents', to_time=int(time.time()) * 1000,
                                                       from_time=int(time.time()) - 86400000):
                try:
                    incidents_assets = incident_raw.get('affected_assets')
                    if not isinstance(incidents_assets, list):
                        incidents_assets = []
                    if not incident_raw.get('description') or not isinstance(incident_raw.get('description'), list):
                        continue
                    for incidents_asset in incidents_assets:
                        try:
                            if not incidents_asset.get('vm_id'):
                                continue
                            if incidents_asset.get('vm_id') not in incidents_dict:
                                incidents_dict[incidents_asset.get('vm_id')] = []
                            incidents_dict[incidents_asset.get('vm_id')].append(incident_raw.get('description'))
                        except Exception:
                            logger.exception(f'Problem with incident asset {incidents_asset}')
                except Exception:
                    logger.exception(f'Problem with incident raw {incident_raw}')
        except Exception:
            logger.exception(f'Problem getting incidents')
        for device_raw in self._get_api_endpoint('assets', status='on'):
            yield device_raw, incidents_dict

    def get_user_list(self):
        try:
            yield from self._get_api_endpoint('system/users')
        except Exception:
            logger.exception(f'Problem fetching users data')

    def _get_api_endpoint(self, endpoint, to_time=None, from_time=None, status=None):
        offset = 0
        response = self._get(endpoint, url_params={'limit': DEVICE_PER_PAGE, 'offset': offset, 'status': status,
                                                   'to_time': to_time, 'from_time': from_time})
        yield from response.get('objects')
        total_count = response.get('total_count')
        offset = DEVICE_PER_PAGE
        number_exception = 0
        while offset < min(MAX_NUMBER_OF_DEVICES, total_count):
            try:
                response = self._get(endpoint, url_params={'limit': DEVICE_PER_PAGE, 'offset': offset, 'status': status,
                                                           'to_time': to_time, 'from_time': from_time})
                if not response.get('objects'):
                    break
                yield from response.get('objects')
                number_exception = 0
            except Exception:
                logger.exception(f'Problem with offset {offset}')
                number_exception += 1
                if number_exception >= 3:
                    break
            offset += DEVICE_PER_PAGE
