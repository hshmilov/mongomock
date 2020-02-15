import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from defender_atp_adapter.consts import RESOURCE_APP_ID_URI

logger = logging.getLogger(f'axonius.{__name__}')


class DefenderAtpConnection(RESTConnection):
    """ rest client for DefenderAtp adapter """

    def __init__(self, *args, tenant_id, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         domain='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._client_id = client_id
        self._client_secret = client_secret
        self._tenant_id = tenant_id

    def _connect(self):
        if not self._client_id or not self._client_secret:
            raise RESTException('No client id or secret')
        response = self._post(f'https://login.windows.net/{self._tenant_id}/oauth2/token',
                              use_json_in_body=False,
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              body_params={'grant_type': 'client_credentials',
                                           'client_id': self._client_id,
                                           'client_secret': self._client_secret,
                                           'resource': RESOURCE_APP_ID_URI
                                           })
        if 'access_token' not in response:
            logger.exception(f'Bad login. Got this response {response}')
            raise RESTException('Bad login Credentials')
        token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {token}'
        self._get('https://api.securitycenter.windows.com/api/machines')

    def get_device_list(self):
        devices_raw = self._get('https://api.securitycenter.windows.com/api/machines')
        for device_raw in devices_raw.get('value') or []:
            try:
                device_id = device_raw.get('id')
                if not device_id:
                    continue
                try:
                    device_raw['users_raw'] = self._get(f'https://api.securitycenter.windows.com/'
                                                        f'api/machines/{device_id}/logonusers').get('value')
                except Exception:
                    logger.debug(f'Problem getting users for {device_raw}')
                try:
                    device_raw['apps_raw'] = self._get(f'https://api.securitycenter.windows.com/'
                                                       f'api/machines/{device_id}/software').get('value')
                except Exception:
                    logger.debug(f'Problem getting software for {device_raw}')
                try:
                    device_raw['vulns_raw'] = self._get(f'https://api.securitycenter.windows.com/'
                                                        f'api/machines/{device_id}/vulnerabilities').get('value')
                except Exception:
                    logger.debug(f'Problem getting vulns for {device_raw}')
            except Exception:
                logger.exception(f'Problem getting extra data for {device_raw}')
            yield device_raw
