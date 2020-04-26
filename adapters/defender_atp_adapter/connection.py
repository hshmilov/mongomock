import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from defender_atp_adapter.consts import RESOURCE_APP_ID_URI, MAX_PAGE_NUM_TO_AVOID_INFINITE_LOOP

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
        self._last_refresh = None
        self._expires_in = None

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
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
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in']) - 5
        self._session_headers['Authorization'] = f'Bearer {token}'

    def _connect(self):
        if not self._client_id or not self._client_secret:
            raise RESTException('No client id or secret')
        self._last_refresh = None
        self._refresh_token()
        self._get('https://api.securitycenter.windows.com/api/machines')

    def _paged_get(self, resource):
        # Take care of paging generically: https://developer.microsoft.com/en-us/graph/docs/concepts/paging
        self._refresh_token()
        result = self._get(resource)
        yield from result['value']

        page_num = 1
        while '@odata.nextLink' in result and page_num < MAX_PAGE_NUM_TO_AVOID_INFINITE_LOOP:
            try:
                result = self._get(result['@odata.nextLink'], force_full_url=True)
                yield from result['value']
                page_num += 1
            except Exception as e:
                logger.exception(f'Problem at page num {page_num}: {str(e)}')
                raise

    # pylint: disable=arguments-differ
    def get_device_list(self, fetch_users, fetch_apps, fetch_vulns):
        devices_raw = self._paged_get('https://api.securitycenter.windows.com/api/machines')
        for device_raw in devices_raw:
            try:
                device_id = device_raw.get('id')
                if not device_id:
                    continue
                try:
                    if fetch_users:
                        self._refresh_token()
                        device_raw['users_raw'] = self._get(f'https://api.securitycenter.windows.com/'
                                                            f'api/machines/{device_id}/logonusers').get('value')
                except Exception:
                    logger.debug(f'Problem getting users for {device_raw}')
                try:
                    if fetch_apps:
                        self._refresh_token()
                        device_raw['apps_raw'] = self._get(f'https://api.securitycenter.windows.com/'
                                                           f'api/machines/{device_id}/software').get('value')
                except Exception:
                    logger.debug(f'Problem getting software for {device_raw}')
                try:
                    if fetch_vulns:
                        self._refresh_token()
                        device_raw['vulns_raw'] = self._get(f'https://api.securitycenter.windows.com/'
                                                            f'api/machines/{device_id}/vulnerabilities').get('value')
                except Exception:
                    logger.debug(f'Problem getting vulns for {device_raw}')
            except Exception:
                logger.exception(f'Problem getting extra data for {device_raw}')
            yield device_raw
