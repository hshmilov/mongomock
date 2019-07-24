import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.adapter_exceptions import ClientConnectionException

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoFirepowerManagementCenterConnection(RESTConnection):
    """ rest client for CiscoFirepowerManagementCenter adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/fmc_platform/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._session_refresh_time = None
        self._session_refresh_count = 0
        self._session_refresh_token = None
        self._domain_uuid = None

    def _refresh_token(self):
        """
        Generate or refresh the 30-minute API authentication token.
        """

        # if we have a valid token, nothing to do
        if self._session_refresh_time and self._session_refresh_time > datetime.datetime.now():
            return

        try:
            # if we have a refresh token and have not hit the 3 refresh limit yet, refresh the current token
            if self._session_refresh_token and self._session_refresh_count < 3:
                response = self._post('auth/refreshtoken',
                                      extra_headers={'X-auth-refresh-token', self._session_refresh_token},
                                      return_response_raw=True,
                                      use_json_in_response=False)
                self._session_refresh_count += 1
            # otherwise, assume we have to generate a new token
            else:
                response = self._post('auth/generatetoken',
                                      do_basic_auth=True,
                                      return_response_raw=True,
                                      use_json_in_response=False)
                self._session_refresh_count = 0
            # get access token value and set refresh token
            response.raise_for_status()
            if 'X-auth-access-token' not in response.headers:
                headers_keys = dict(response.headers).keys()
                logger.error(f'Bad headers {response.headers}')
                raise RESTException(f'Bad Headers in response {str(headers_keys)}')
            access_token = response.headers['X-auth-access-token']
            self._session_refresh_token = response.headers['X-auth-refresh-token']

            # set token expiry time to API-provided 30 minutes
            expires_in = 1800
            self._session_refresh_time = datetime.datetime.now() + datetime.timedelta(seconds=(expires_in - 1))

            # if _domain_uuid has never been set, set it since API calls have to go to base += domain/self._domain_uuid
            if not self._domain_uuid:
                self._domain_uuid = response.headers['DOMAIN_UUID']

        except Exception as e:
            message = f'Error parsing response: {str(e)}'
            logger.exception(message)
            raise

        # update access token to new/refreshed version
        self._session_headers['X-auth-access-token'] = access_token

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        # if creds are valid, go through the token refresh/generate flow
        self._refresh_token()

        # Try to access required API endpoints to check that API token has correct permissions
        try:
            self._get(f'domain/{self._domain_uuid}/devices/devicerecords')
        except RESTException as e:
            message = f'Unable to access a required API endpoint: {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    def get_device_list(self):
        self._refresh_token()
        response = self._get(f'domain/{self._domain_uuid}/devices/devicerecords')

        offset = response['paging']['offset']
        pages = response['paging']['pages']
        items = response['items']

        # use the fact that API response contains full URLs for individual objects when using /devices/devicerecords
        for item in items:
            try:
                self._refresh_token()
                yield self._get(item['links']['self'], force_full_url=True)
            except Exception:
                logger.exception(f'Encountered malformed Device item.')
        offset += 1
        while offset < pages:
            try:
                response = self._get(f'domain/{self._domain_uuid}/devices/devicerecords', url_params={'offset': offset})
                if not response:
                    break
                for item in items:
                    try:
                        self._refresh_token()
                        yield self._get(item['links']['self'], force_full_url=True)
                    except Exception:
                        logger.exception(f'Encountered malformed Device item.')
                offset += 1
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                break
