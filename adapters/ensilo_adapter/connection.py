import logging
logger = logging.getLogger(f"axonius.{__name__}")
import requests

from ensilo_adapter.exceptions import EnsiloAlreadyConnected, EnsiloConnectionError, EnsiloNotConnected, \
    EnsiloRequestException


class EnsiloConnection(object):
    def __init__(self, domain, verify_ssl):
        """ Initializes a connection to Ensilo using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Ensilo
        """
        self.domain = domain
        self.verify_ssl = verify_ssl
        url = domain
        if not url.endswith('/'):
            url += '/'

        url += "management-rest/"
        self.url = url
        self.session = None
        self.username = None
        self.password = None
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
            raise EnsiloAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            response = session.get(self._get_url_request('inventory/list-collectors'),
                                   auth=(self.username, self.password), verify=self.verify_ssl)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise EnsiloConnectionError(str(e))
        else:
            raise EnsiloConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _get(self, name, params=None):
        """ Serves a GET request to Ensilo API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise EnsiloNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params, headers=self.headers,
                                    auth=(self.username, self.password),  verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise EnsiloRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Ensilo's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        devices_list = []
        try:
            devices_list += self._get('inventory/list-collectors?itemsPerPage=2000&pageNumber=0')
        except:
            logger.exception("Page 0 Unsopported in Ensilo")
        try:
            # If we won't get error, let's stop after million devices
            for page_number in range(1, 500):
                devices_list += self._get('inventory/list-collectors?itemsPerPage=2000&pageNumber=' + str(page_number))
        except:
            pass
        return devices_list

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
