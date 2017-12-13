import requests

from sentinelone_exceptions import SentinelOneAlreadyConnected, SentinelOneConnectionError, SentinelOneNotConnected, \
    SentinelOneRequestException


class SentinelOneConnection(object):
    def __init__(self, logger, domain):
        """ Initializes a connection to SentinelOne using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for SentinelOne
        """
        self.logger = logger
        self.domain = domain
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        url += 'web/api/v1.6/'
        self.url = url
        self.token = None
        self.session = None
        self.username = None
        self.password = None
        self.headers = None

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
        token_type = 'APIToken ' if self.username is None else 'Token '
        self.headers = {'Authorization': token_type + self.token, 'Content-Type': 'application/json'}

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
            raise SentinelOneAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            connection_dict = {'username': self.username,
                               'password': self.password}
            response = session.post(self._get_url_request('users/login'), json=connection_dict)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise SentinelOneConnectionError(str(e))
            response = response.json()
            if 'token' not in response:
                error = response.get('error', 'unknown connection error')
                message = response.get('message', '')
                if message:
                    error += ': ' + message
                raise SentinelOneConnectionError(error)
            self.set_token(response['token'])
        else:
            assert self.token is not None
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def logout(self):
        """ Logs out of the service

            :return: whether the logout was successful
            :rtype: bool
        """
        response = self._post('users/logout')
        success = response.get('success', False)
        if success:
            self.close()
        return success

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _post(self, name, params=None):
        """ Serves a POST request to SentinelOne API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise SentinelOneNotConnected()
        params = params or {}
        response = self.session.post(self._get_url_request(name), json=params, headers=self.headers)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise SentinelOneRequestException(str(e))
        return response.json()

    def _get(self, name, params=None):
        """ Serves a GET request to SentinelOne API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise SentinelOneNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params, headers=self.headers)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise SentinelOneRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses SentinelOne's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        return self._get('agents', kwargs)

    def get_device_iterator(self, **kwargs):
        """ Returns an iterator of agents

        :param dict kwargs: api query *string* parameters (ses SentinelOne's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        return self._get('agents/iterator', kwargs)

    def get_user_list(self):
        """ Returns a list of all users

        :return: the response
        :rtype: dict
        """
        return self._get('users')

    def get_user_by_username(self, name):
        """ Returns a single users details by its name

        :return: the response (or None if not found)
        :rtype: dict or None
        """
        users = self.get_user_list()
        for user in users:
            if user['username'] == name:
                return user
        return None

    def get_api_token_details(self, user_id):
        """ Returns the api token details of a user

        :param: str user_id: the user id
        :return: the response
        :rtype: dict
        """
        return self._get('users/{0}/api-token-details'.format(user_id))

    def generate_api_token(self):
        """ Generates a new API token for the logged-on user

        :return: the response
        :rtype: dict
        """
        return self._post('users/generate-api-token')

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
