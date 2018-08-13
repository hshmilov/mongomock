from axonius.clients.rest.connection import RESTConnection
from tenable_io_adapter import consts
import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.clients.rest.exception import RESTException
import time
from axonius.utils.parsing import make_dict_from_csv


class TenableIoConnection(RESTConnection):

    def __init__(self, *args, access_key: str = "",  secret_key: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._access_key = access_key
        self._secret_key = secret_key
        if self._username is not None and self._username != "" and self._password is not None and self._password != "":
            # We should use the user and password
            self._should_use_token = True
        elif self._access_key is not None and self._access_key != "" and \
                self._secret_key is not None and self._secret_key != "":
            # We should just use the given api keys
            self._should_use_token = False
            self._set_api_headers()
        else:
            raise RESTException("Missing user/password or api keys")

    def _set_token_headers(self, token):
        """ Sets the API token, in the appropriate header, for valid requests

        :param str token: API Token
        """
        self._token = token
        self._session_headers['X-Cookie'] = 'token={0}'.format(token)

    def _set_api_headers(self):
        """ Setting headers to include the given api key
        """
        self._permanent_headers['X-ApiKeys'] = f'accessKey={self._access_key}; secretKey={self._secret_key}'

    def _connect(self):
        if self._should_use_token is True:
            response = self._post('session', body_params={'username': self._username, 'password': self._password})
            if 'token' not in response:
                error = response.get('errorCode', 'Unknown connection error')
                message = response.get('errorMessage', '')
                if message:
                    error = '{0}: {1}'.format(error, message)
                raise RESTException(error)
            self._set_token_headers(response['token'])
        else:
            self._get('scans')

    def get_device_list(self):
        file_id = self._get("workbenches/export", url_params={'format': 'csv', 'report': 'vulnerabilities', 'chapter': 'vuln_by_asset',
                                                              'date_range': consts.DAYS_FOR_VULNS_IN_CSV})["file"]
        status = self._get(f"workbenches/export/{file_id}/status")["status"]
        sleep_times = 0
        while status != 'ready' and sleep_times < consts.NUMBER_OF_SLEEPS:
            time.sleep(consts.TIME_TO_SLEEP)
            status = self._get(f"workbenches/export/{file_id}/status")["status"]
            sleep_times += 1
        return make_dict_from_csv(self._get(f"workbenches/export/{file_id}/download", use_json_in_response=False).decode('utf-8'))
