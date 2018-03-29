import requests

from secdo_adapter.exceptions import SecdoAlreadyConnected, SecdoConnectionError, SecdoNotConnected, SecdoRequestException


class SecdoConnection(object):
    def __init__(self, logger, domain, verify_ssl):
        """ Initializes a connection to Secdo using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Secdo
        """
        self.logger = logger
        self.domain = domain
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        url += "publicapiv2/run/command/"
        self.url = url
        self.verify_ssl = verify_ssl
        self.session = None
        self.company = None
        self.api_key = None
        self.headers = {'Content-Type': 'application/json'}

    def _get_url_request(self, request_name):
        """ Builds and returns the full url for the request

        :param request_name: the request name
        :return: the full request url
        """
        return self.url + request_name

    def set_credentials(self, company, api_key):
        """ Set the connection credentials

        :param str company: The Company
        :param str password: The api key
        """
        self.company = company
        self.api_key = api_key

    @property
    def is_connected(self):
        return self.session is not None

    def connect(self):
        """ Connects to the service """
        if self.is_connected:
            raise SecdoAlreadyConnected()
        session = requests.Session()
        self.headers["COMMAND-NAME"] = "get_agents"
        self.headers["API-KEY"] = self.api_key
        if self.company is not None and self.api_key is not None:
            connection_dict = {'company': self.company}
            response = session.post(self._get_url_request(''), json=connection_dict,
                                    headers=self.headers, verify=self.verify_ssl)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise SecdoConnectionError(str(e))
        else:
            raise SecdoConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _post(self, name, params=None):
        """ Serves a POST request to Secdo API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise SecdoNotConnected()
        params = params or {}
        response = self.session.post(self._get_url_request(name), json=params,
                                     headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise SecdoRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Secdo's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        connection_dict = {'company': self.company}
        return self._post('', params=connection_dict)["agents"]

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
