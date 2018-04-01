import logging
logger = logging.getLogger(f"axonius.{__name__}")
import requests
import base64

from desktop_central_adapter.exceptions import DesktopCentralAlreadyConnected, DesktopCentralConnectionError, \
    DesktopCentralNotConnected, \
    DesktopCentralRequestException


class DesktopCentralConnection(object):
    def __init__(self, domain, verify_ssl):
        """ Initializes a connection to DesktopCentral using its rest API

        :param str domain: domain address for DesktopCentral
        :param bool verify_ssl
        """
        self.domain = domain
        url = domain
        if not url.endswith('/'):
            url += '/'
        url += 'api/1.0/'
        self.url = url
        self.token = None
        self.session = None
        self.username = None
        self.password = None
        self.headers = {'Content-Type': 'application/json'}
        self.verify_ssl = verify_ssl

    def set_credentials(self, username, password):
        """ Set the connection credentials

        :param str username: The username
        :param str password: The password
        """
        self.username = username
        self.password = password

    def set_token(self, token):
        """ Sets the API token (as the connection credentials)

        :param str token: API Token
        """
        self.token = token
        self.headers = {'Authorization': self.token, 'Content-Type': 'application/json'}

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
            raise DesktopCentralAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            connection_dict = {'username': self.username,
                               'password': str(base64.b64encode(bytes(self.password, "utf-8")), encoding="utf-8"),
                               "auth_type": "local_authentication"}
            response = session.post(self._get_url_request('desktop/authentication'),
                                    json=connection_dict, verify=self.verify_ssl)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise DesktopCentralConnectionError(str(e))
            response = response.json()
            if (('message_response' not in response or 'status' not in response
                 or 'message_version' not in response or 'message_version' not in response)
                    or (response['status'] != 'success')):
                raise DesktopCentralConnectionError("Unknown connection error in authentication")
            token = response["message_response"]["authentication"]["auth_data"]["auth_token"]
            self.set_token(token)
        else:
            assert self.token is not None
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _post(self, name, params=None):
        """ Serves a POST request to DesktopCentral API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise DesktopCentralNotConnected()
        params = params or {}
        response = self.session.post(self._get_url_request(name), json=params,
                                     headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise DesktopCentralRequestException(str(e))
        return response.json()

    def _get(self, name, params=None):
        """ Serves a GET request to DesktopCentral API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise DesktopCentralNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params,
                                    headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise DesktopCentralRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses DesktopCentral's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        return self._get('som/computers', kwargs)["message_response"]["computers"]

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
