from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from sentinelone_adapter import consts
import logging
logger = logging.getLogger(f"axonius.{__name__}")


class SentinelOneConnection(RESTConnection):
    def set_token(self, token):
        """ Sets the API token (as the connection credentials)

        :param str token: API Token
        """
        self._token = token
        if (self._username is None or self._username == ""):
            token_type = 'ApiToken '
            self._permanent_headers['Authorization'] = token_type + self._token
        else:
            token_type = 'Token '
            self._session_headers['Authorization'] = token_type + self._token

    def _connect(self):
        if self._username is not None and self._username != ""\
                and self._password is not None and self._password != "":
            connection_dict = {'username': self._username,
                               'password': self._password}
            response = self._post('users/login', body_params=connection_dict)
            if 'token' not in response:
                error = response.get('error', 'unknown connection error')
                message = response.get('message', '')
                if message:
                    error += ': ' + message
                raise RESTException(error)
            self.set_token(response['token'])
        else:
            assert self._token is not None

    def get_device_list(self):
        start_offset = 0
        response = self._get('agents', url_params={"limit": consts.DEVICE_PER_PAGE,
                                                   "skip": start_offset})
        yield from response["data"]
        total_devices = response["pagination"]["totalItems"]
        start_offset += consts.DEVICE_PER_PAGE
        while start_offset < total_devices and start_offset < consts.MAX_DEVICES:
            try:
                yield from self._get('agents', url_params={"limit": consts.DEVICE_PER_PAGE,
                                                           "skip": start_offset})["data"]
            except Exception:
                logger.exception(f"Problem with offset {start_offset}")
            start_offset += consts.DEVICE_PER_PAGE
