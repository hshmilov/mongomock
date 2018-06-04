import requests
import logging
logger = logging.getLogger(f"axonius.{__name__}")

from carbonblack_response_adapter.exceptions import CarbonblackResponseAlreadyConnected, CarbonblackResponseConnectionError,\
    CarbonblackResponseNotConnected, \
    CarbonblackResponseRequestException


class CarbonblackResponseConnection(object):
    def __init__(self, domain, verify_ssl):
        """ Initializes a connection to CarbonblackResponse using its rest API

        :param str domain: domain address for CarbonblackResponse
        """
        self.domain = domain
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url

        if not url.endswith('/'):
            url += '/'
        url += 'api/'
        self.url = url
        self.session = None
        self.verify_ssl = verify_ssl
        self.username = None
        self.password = None
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def set_credentials(self, username, password):
        """ Set the connection credentials

        :param str username: The username
        """
        self.username = username
        self.password = password

    def _get_url_request(self, request_name):
        """ Builds and returns the full url for the request

        :param request_name: the request name
        :return: the full request url
        """
        return self.url + request_name

    @property
    def is_connected(self):
        return self.session is not None

    def connect(self):
        """ Connects to the service """
        if self.is_connected:
            raise CarbonblackResponseAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            try:
                response = session.get(self._get_url_request('auth'), verify=self.verify_ssl, headers=self.headers,
                                       auth=requests.auth.HTTPDigestAuth(self.username, self.password), timeout=(5, 30))
                response.raise_for_status()
                logger.debug(f"Got auth response {response.text}")
            except requests.HTTPError as e:
                raise CarbonblackResponseConnectionError(str(e))
        else:
            raise CarbonblackResponseConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _get(self, name, params=None):
        """ Serves a GET request to CarbonblackResponse API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise CarbonblackResponseNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params,
                                    headers=self.headers, verify=self.verify_ssl, timeout=(5, 30))
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise CarbonblackResponseRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses CarbonblackResponse's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        return self._get("v1/sensor")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
