import requests

from symantec_exceptions import SymantecAlreadyConnected, SymantecConnectionError, SymantecNotConnected, \
    SymantecRequestException

DEFAULT_SYMANTEC_PORT = 8446


class SymantecConnection(object):
    def __init__(self, logger, domain, port):
        """ Initializes a connection to Symantec using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Symantec
        """
        self.logger = logger
        self.domain = domain
        self.port = port if port is not None else DEFAULT_SYMANTEC_PORT
        assert type(self.port) == int, "the port {self.port} is not a valid int!"
        url = domain + ':' + str(self.port)
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        url += 'sepm/api/v1/'
        self.url = url
        self.token = None
        self.adminId = None
        self.session = None
        self.username = None
        self.password = None
        self.headers = {'Content-Type': 'application/json'}

    def set_token(self, token, adminId):
        """ Sets the API token (as the connection credentials)

        :param str token: API Token
        :param str adminId: user adminId
        """
        self.token = token
        self.adminId = adminId
        self.headers = {'Authorization': 'Bearer ' + self.token}

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
            raise SymantecAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            connection_dict = {
                'username': self.username,
                'password': self.password,
                "domain": ""
            }
            response = session.post(self._get_url_request('identity/authenticate'), headers={'Content-Type': 'application/json'},
                                    json=connection_dict,
                                    verify=False)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise SymantecConnectionError(str(e))
            response = response.json()
            if 'token' not in response:
                error = response.get('errorCode', 'unknown connection error')
                message = response.get('errorMessage', '')
                if message:
                    error += ': ' + message
                raise SymantecConnectionError(error)
            self.set_token(response['token'], response['adminId'])
            self.session = session
        else:
            assert self.token is not None, "no username or password and no token"

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            try:
                self.logout()
            except:
                pass
            self.close()

    def logout(self):
        """ Logs out of the service

            :return: whether the logout was successful
            :rtype: bool
        """
        response = self.session.post(self._get_url_request('identity/logout'), headers={'Content-Type': 'application/json'},
                                     json={'token': self.token,
                                           'adminId': self.adminId})
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise SymantecRequestException(str(e))
        self.close()
        return True

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None
        self.token = None
        self.adminId = None

    def _post(self, name, params=None, headers=None):
        """ Serves a POST request to Symantec API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :param dict headers: headers for the request
        :return: the response json
        :rtype: dict
        """
        if not self.is_connected:
            raise SymantecNotConnected()
        headers = headers if headers is not None else self.headers
        params = params if params is not None else {}
        response = self.session.post(self._get_url_request(name), json=params, headers=headers)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise SymantecRequestException(str(e))
        return response.json()

    def _get(self, name, params=None, headers=None):
        """ Serves a GET request to Symantec API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :param dict headers: headers for the request
        :return: the response json
        :rtype: dict
        """
        if not self.is_connected:
            raise SymantecNotConnected()
        headers = headers if headers is not None else self.headers
        params = params if params is not None else {}
        response = self.session.get(self._get_url_request(name), params=params, headers=headers)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise SymantecRequestException(str(e))
        return response.json()

    def get_device_iterator(self, **kwargs):
        """ Returns an iterator of agents

        :param dict kwargs: api query *string* parameters (ses SentinelOne's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        return self._get('computers', kwargs)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.logout()
