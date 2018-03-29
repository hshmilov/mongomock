import requests

from minerva_adapter.exceptions import MinervaAlreadyConnected, MinervaConnectionError, MinervaNotConnected, \
    MinervaRequestException


class MinervaConnection(object):
    def __init__(self, logger, domain, is_ssl, verify_ssl):
        """ Initializes a connection to Minerva using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Minerva
        :param bool verify_ssl Verify the ssl
        """
        self.logger = logger
        self.domain = domain
        self._is_ssl = is_ssl
        url = domain
        if self._is_ssl and (not url.lower().startswith('https://')):
            url = 'https://' + url

        if not self._is_ssl and (not url.lower().startswith('http://')):
            url = 'http://' + url
        if not url.endswith('/'):
            url += '/'
        url += 'owl/api/'
        self.url = url
        self.session = None
        self.username = None
        self.password = None
        self.verify_ssl = verify_ssl
        self.headers = {'Content-Type': 'application/json'}

    def set_credentials(self, username, password):
        """ Set the connection credentials

        :param str username: The username
        :param str password: The password
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
            raise MinervaAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            connection_dict = {'username': self.username,
                               'password': self.password}
            response = session.post(self._get_url_request('login'), json=connection_dict, verify=self.verify_ssl)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise MinervaConnectionError(str(e))
        else:
            raise MinervaConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _post(self, name, params=None):
        """ Serves a POST request to Minerva API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise MinervaNotConnected()
        params = params or {}
        response = self.session.post(self._get_url_request(name), json=params,
                                     headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise MinervaRequestException(str(e))
        return response.json()

    def _get(self, name, params=None):
        """ Serves a GET request to Minerva API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise MinervaNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params,
                                    headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise MinervaRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Minerva's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        return self._post('endpoints', params={'page': {'index': 1, 'length': 100000}})

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
