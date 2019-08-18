import datetime
import time
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.haveibeenpwned.consts import HAVEIBEENPWNED_DOMAIN

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
        time.sleep(2)
        url = f'api/v3/breachedaccount/{email}'
        if self._internal_haveibeenpwned:
            self._refresh_token()
            url = f'hibp/api/v3/breachedaccount/{email}'
        return self._get(url)

    def _connect(self):
        pass

    def get_device_list(self):
        pass
