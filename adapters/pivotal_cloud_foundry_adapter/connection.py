import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from pivotal_cloud_foundry_adapter.consts import URL_DEFAULT_API_PREFIX, DEVICE_PER_PAGE, URL_API_APP_STAT

logger = logging.getLogger(f'axonius.{__name__}')


class PivotalCloudFoundryConnection(RESTConnection):
    """ rest client for PivotalCloudFoundry adapter """

    def __init__(self, *args, uaa_domain, **kwargs):
        super().__init__(*args, url_base_prefix=URL_DEFAULT_API_PREFIX,
                         headers={'Content-Type': 'application/x-www-form-urlencoded',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = None
        self._refresh_token = None
        self._session_refresh = None
        self._uaa_path = uaa_domain

    def _get_refresh_token(self):
        body_params = {
            'grant_type': 'refresh_token',
            'refresh_token': self._refresh_token,
            'client_id': 'cf',
            'client_secret': ''
        }
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return
        self._get_token(body_params)

    def _get_token_with_credentials(self):
        body_params = {
            'grant_type': 'password',
            'username': self._username,
            'password': self._password,
            'client_id': 'cf',
            'client_secret': ''
        }
        self._get_token(body_params)

    def _get_token(self, body_params):
        try:
            response = self._post(self._uaa_path, body_params=body_params,
                                  force_full_url=True, use_json_in_body=False)
            if not isinstance(response, dict) or \
                    'access_token' not in response or \
                    'refresh_token' not in response or \
                    'expires_in' not in response:
                raise RESTException(f'Invalid response: {response}')

            self._token = response.get('access_token')
            self._refresh_token = response.get('refresh_token')
            self._session_refresh = datetime.datetime.now() + datetime.timedelta(
                seconds=(int(response.get('expires_in')) - 50))

            self._session_headers = {
                'Authorization': f'Bearer {self._token}'
            }

        except Exception:
            raise ValueError(f'Error: Failed getting token, invalid request was made.')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._get_token_with_credentials()
            self._get('apps', url_params={'page': 1, 'per_page': 1})
        except Exception:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials')

    # pylint: disable=logging-format-interpolation
    def _paginated_get(self):
        try:
            url_params = {
                'page': 1,
                'per_page': DEVICE_PER_PAGE
            }
            while True:
                self._get_refresh_token()
                response = self._get('apps', url_params=url_params)
                if not response.get('resources'):
                    break

                for resource in response['resources']:
                    self._get_refresh_token()
                    if not resource.get('guid'):
                        raise ValueError(f'Invalid response: {response}')

                    self._get_refresh_token()
                    app = self._get(URL_API_APP_STAT.format(resource['guid']))
                    for process in app['resources']:
                        if 'guid' in resource and 'name' in resource:
                            process['guid'] = resource['guid']
                            process['name'] = resource['name']
                        yield process

                url_params['page'] += 1

        except Exception as err:
            logger.exception(f'Invalid request made, {str(err)}')
            raise

    def get_device_list(self):
        self._get_refresh_token()
        try:
            yield from self._paginated_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
