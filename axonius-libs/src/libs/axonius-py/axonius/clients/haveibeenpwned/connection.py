import datetime
import time
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.haveibeenpwned.consts import HAVEIBEENPWNED_DOMAIN, MAX_RATE_LIMIT_TRY

logger = logging.getLogger(f'axonius.{__name__}')


class HaveibeenpwnedConnection(RESTConnection):
    """ rest client for Haveibeenpwned adapter """

    def __init__(self, *args,  domain_preferred=None, **kwargs):
        self._internal_haveibeenpwned = domain_preferred and ';' in domain_preferred
        self._auth_url = None
        if self._internal_haveibeenpwned:
            domain_preferred, self._auth_url = domain_preferred.split(';')[0], domain_preferred.split(';')[1]
        super().__init__(*args, domain=domain_preferred or HAVEIBEENPWNED_DOMAIN,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        if self._internal_haveibeenpwned:
            if len(self._username.split(';')) > 1:
                self._username, self._app_id = self._username.split(';')[0], self._username.split(';')[1]
            else:
                self._app_id = ''
            if len(self._password.split(';')) > 1:
                self._password, self._app_secret = self._password.split(';')[0], self._password.split(';')[1]
            else:
                self._app_secret = ''
        self._session_refresh = None
        if self._apikey:
            self._permanent_headers['hibp-api-key'] = self._apikey

    def _refresh_token(self):
        """
        Temporarily adjusts the connection properties to handle a specific customer's
        internal API proxy mechanism that sits in front of haveibeenpwned. This should be
        refactored ASAP...
        """
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return
        self._username, self._password = self._apikey.split(':')
        self._session_headers = {'Content-Type': 'application/x-www-form-urlencoded',
                                 'Accept': 'application/json'}

        response = self._post(self._auth_url,
                              force_full_url=True,
                              body_params=f'grant_type=password&username={self._app_id}&password={self._app_secret}',
                              use_json_in_body=False,
                              do_basic_auth=True)
        try:
            access_token = response['access_token']
            token_type = response['token_type']
            expires_in = response['expires_in']
            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=(expires_in - 1))
        except Exception as e:
            message = f'Error parsing response: {str(e)}'
            logger.exception(message)
            raise message
        if token_type == 'Bearer' and expires_in > 0:
            self._session_headers = {'Content-Type': 'application/json',
                                     'Accept': 'application/json',
                                     'Authorization': access_token}
        else:
            message = f'Invalid access_token type or token already expired!'
            logger.exception(message)
            raise message

    def get_breach_account_info(self, email):
        time.sleep(1.5)
        url = f'api/v3/breachedaccount/{email}?truncateResponse=false'
        if self._internal_haveibeenpwned:
            self._refresh_token()
            url = f'hibp/' + url
        return self._hibp_get(url)

    def _hibp_get(self, path, url_params=None):
        for try_ in range(MAX_RATE_LIMIT_TRY):
            response = self._get(path, url_params=url_params,
                                 raise_for_status=False,
                                 return_response_raw=True,
                                 use_json_in_response=False
                                 )
            if response.status_code == 429:
                try:
                    retry_after = response.headers.get('Retry-After') or response.headers.get('retry-after')
                    if retry_after:
                        logger.info(f'Got 429, sleeping for {retry_after}')
                    else:
                        logger.info(f'Got 429 with no retry-after header, sleeping for 3')
                        retry_after = 2
                    time.sleep(int(retry_after) + 1)
                except Exception:
                    time.sleep(6)
                continue
            break
        else:
            raise RESTException(f'Failed to fetch path {path} because rate limit')
        return self._handle_response(response)

    def _connect(self):
        pass

    def get_device_list(self):
        pass
