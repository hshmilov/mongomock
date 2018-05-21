import requests

from infoblox_adapter.exceptions import InfobloxAlreadyConnected, InfobloxConnectionError, InfobloxNotConnected, \
    InfobloxRequestException
from urllib3.util.url import parse_url
import logging
logger = logging.getLogger(f"axonius.{__name__}")


class InfobloxConnection(object):
    def __init__(self, domain, verify_ssl):
        """ Initializes a connection to Infoblox using its rest API

        :param str domain: domain address for Infoblox
        :param bool verify_ssl Verify the ssl
        """
        self.domain = domain
        url = parse_url(domain)
        self.url = f"https://{url.host}/wapi/v2.7/"
        self.session = None
        self.username = None
        self.password = None
        self.verify_ssl = verify_ssl
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

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
            raise InfobloxAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            response = session.get(self._get_url_request('zone_auth_return_as_object=1'),
                                   auth=(self.username, self.password), verify=self.verify_ssl)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise InfobloxConnectionError(str(e))
        else:
            raise InfobloxConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _post(self, name, params=None):
        """ Serves a POST request to Infoblox API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise InfobloxNotConnected()
        params = params or {}
        response = self.session.post(self._get_url_request(name), json=params,
                                     headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise InfobloxRequestException(str(e))
        return response.json()

    def _get(self, name, params=None):
        """ Serves a GET request to Infoblox API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise InfobloxNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params,
                                    headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise InfobloxRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Infoblox's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        networks = []
        # These are the reasonable numbers of cidrs in networks
        for cidr in range(8, 28):
            try:
                networks.extend([network_raw["network"] for network_raw in
                                 self._get(f"network?network=.0/{cidr}&_return_as_object=1")["result"]])
            except Exception:
                logger.exception(f"Problem in networks with CIDR {cidr}")
        for network in networks:
            try:
                for device_raw in self._get(f"ipv4address?network={network}&_return_as_object=1")["result"]:
                    yield device_raw
            except Exception:
                logger.exception(f"Problem getting network {network}")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
