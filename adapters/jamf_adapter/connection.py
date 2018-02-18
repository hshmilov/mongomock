import requests
import base64
from jamf_adapter.exceptions import JamfConnectionError, JamfRequestException
from jamf_adapter.search import JamfAdvancedSearch
from jamf_adapter import consts
import xml.etree.cElementTree as ET
from axonius.utils.xml2json_parser import Xml2Json


class JamfConnection(object):
    def __init__(self, logger, domain, http_proxy=None, https_proxy=None):
        """ Initializes a connection to Jamf using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Jamf
        """
        self.logger = logger
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        self.url = url + 'JSSResource/'
        self.headers = {}
        self.auth = None
        self.proxies = {}
        if http_proxy is not None:
            self.proxies['http'] = http_proxy
        if https_proxy is not None:
            self.proxies['https'] = https_proxy
        self.logger.info(f"Proxies: {self.proxies}")

    def set_credentials(self, username, password):
        """ Set the connection credentials

        :param str username: The username
        :param str password: The password
        """
        self.auth = username + ":" + password
        self.headers['authorization'] = 'Basic ' + base64.b64encode(self.auth.encode()).decode()

    def get_url_request(self, request_name):
        """ Builds and returns the full url for the request

        :param request_name: the request name
        :return: the full request url
        """
        return self.url + request_name

    def connect(self):
        """ Connects to the service """

        if self.auth is None:
            raise JamfConnectionError(f"Username and password is None")
        response = self.get("accounts")

        # the only case where we get 200 and no accounts is if the domain is not the Jamf one
        # i.e. someone lied in the domain and somehow the page <domain>/JSSResource/accounts exists
        if 'accounts' not in response:
            raise JamfConnectionError(str(response))

    def __del__(self):
        self.logout()

    def logout(self):
        """ Logs out of the service"""
        self.close()

    def close(self):
        """ Closes the connection """

    def _post(self, name, headers=None, data=None):
        """ Serves a POST request to Jamf API

        :param str name: the name of the page to request
        :param dict headers: the headers for the post request
        :param str data: the body of the request
        :return: the service response or raises an exception if it's not 200
        """
        response = requests.post(self.get_url_request(name), headers=headers, data=data, proxies=self.proxies)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise JamfRequestException(str(e))
        return response.json()

    def jamf_request(self, request_method, url_addition, data, error_message):
        post_headers = self.headers
        post_headers['Content-Type'] = 'application/xml'
        response = request_method(self.get_url_request(url_addition),
                                  headers=post_headers,
                                  data=data,
                                  proxies=self.proxies)
        try:
            response.raise_for_status()
            response_tree = ET.fromstring(response.text)
            int(response_tree.find("id").text)
        except ValueError:
            # conversion of the query id to int failed
            self.logger.exception(error_message + f": {response.text}")
            raise JamfRequestException(error_message + f": {response.text}")
        except Exception as e:
            # any other error during creation of the query or during the conversion
            self.logger.exception(error_message)
            raise JamfRequestException(error_message + str(e))

    def get(self, name, headers=None):
        """ Serves a POST request to Jamf API

        :param str name: the name of the page to request
        :param dict headers: the headers for the post request
        :return: the service response or raises an exception if it's not 200
        """
        headers = headers or self.headers
        response = requests.get(self.get_url_request(name), headers=headers, proxies=self.proxies)
        try:
            response.raise_for_status()
            return Xml2Json(response.text).result
        except requests.HTTPError as e:
            raise JamfRequestException(str(e))

    def _get_jamf_devices(self, url, data, xml_name, device_list_name, device_type):
        """ Returns a list of all computers

        :return: the response
        :rtype: list of computers
        """
        search = JamfAdvancedSearch(self, url, data)
        # update has succeeded or an exception would have been raised
        with search:
            devices = search.search_results[xml_name][device_list_name].get(device_type, [])

        return [devices] if type(devices) == dict else devices

    def get_devices(self):
        """ Returns a list of all agents
        :return: the response
        :rtype: list of computers and phones
        """
        # Getting all devices at once so no progress is logged
        computers = self._get_jamf_devices(
            url=consts.ADVANCED_COMPUTER_SEARCH_URL,
            data=consts.ADVANCED_COMPUTER_SEARCH,
            xml_name=consts.ADVANCED_COMPUTER_SEARCH_XML_NAME,
            device_list_name=consts.ADVANCED_COMPUTER_SEARCH_DEVICE_LIST_NAME,
            device_type=consts.COMPUTER_DEVICE_TYPE)

        mobile_devices = self._get_jamf_devices(
            url=consts.ADVANCED_MOBILE_SEARCH_URL,
            data=consts.ADVANCED_MOBILE_SEARCH,
            xml_name=consts.ADVANCED_MOBILE_SEARCH_XML_NAME,
            device_list_name=consts.ADVANCED_MOBILE_SEARCH_DEVICE_LIST_NAME,
            device_type=consts.MOBILE_DEVICE_TYPE)

        return computers + mobile_devices
