import requests
import xml.etree.ElementTree as ET

from bigfix_adapter.exceptions import BigfixAlreadyConnected, BigfixConnectionError, BigfixNotConnected, \
    BigfixRequestException


class BigfixConnection(object):
    def __init__(self, logger, domain, verify_ssl):
        """ Initializes a connection to Bigfix using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Bigfix
        """
        self.logger = logger
        self.domain = domain
        self.verify_ssl = verify_ssl
        url = domain
        if not url.endswith('/'):
            url += '/'
        url += 'api/'
        self.url = url
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
            raise BigfixAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            connection_dict = {'username': self.username,
                               'password': self.password}
            response = session.get(self._get_url_request('computers'), auth=(self.username, self.password),
                                   verify=self.verify_ssl)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise BigfixConnectionError(str(e))
        else:
            raise BigfixConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _get(self, name, params=None, use_full_path=False):
        """ Serves a GET request to Bigfix API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise BigfixNotConnected()
        params = params or {}
        if use_full_path:
            full_url = name
        else:
            full_url = self._get_url_request(name)
        response = self.session.get(full_url, params=params, headers=self.headers)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise BigfixRequestException(str(e))
        return response.content

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Bigfix's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        xml_computers = ET.fromstring(self._get('computers'))
        computers_resources_list = []
        for computer_node in xml_computers:
            if computer_node.tag == 'Computer':
                computer_resource = computer_node.attrib.get('Resource')
                if computer_resource:
                    computers_resources_list.append(self._get(computer_resource, use_full_path=True))
        return computers_resources_list

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
