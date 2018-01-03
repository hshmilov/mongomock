import requests
import base64
from jamf_exceptions import JamfConnectionError, JamfRequestException
from jamf_search import JamfAdvancedSearch
import jamf_consts
from json import JSONDecodeError
from jamf_xml_parser import Xml2Json


class JamfConnection(object):
    def __init__(self, logger, domain):
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
        self.headers = {'Accept': 'application/json'}
        self.auth = None

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
        response = self._get("accounts", headers=self.headers)

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
        response = requests.post(self.get_url_request(name), headers=headers, data=data)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise JamfRequestException(str(e))
        return response.json()

    def _get(self, name, headers=None):
        """ Serves a POST request to Jamf API

        :param str name: the name of the page to request
        :param dict headers: the headers for the post request
        :return: the service response or raises an exception if it's not 200
        """
        response = requests.get(self.get_url_request(name), headers=headers)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise JamfRequestException(str(e))
        try:
            return response.json()
        except JSONDecodeError:
            return Xml2Json(response.text).result

    def _get_jamf_devices(self, url, data, xml_name, device_list_name, headers):
        """ Returns a list of all computers

        :return: the response
        :rtype: list of computers
        """
        search = JamfAdvancedSearch(self, url, data, headers)
        # update has succeeded or an exception would have been raised
        with search:
            try:
                response = search.search_results.json()
            except JSONDecodeError:
                response = Xml2Json(search.search_results.text).result
            return response[xml_name][device_list_name]

    def get_devices(self):
        """ Returns a list of all agents
        :return: the response
        :rtype: list of computers and phones
        """
        non_json_headers = self.headers.copy()
        non_json_headers.pop("Accept")
        computers = self._get_jamf_devices(url=jamf_consts.ADVANCED_COMPUTER_SEARCH_URL,
                                           data=jamf_consts.ADVANCED_COMPUTER_SEARCH,
                                           xml_name=jamf_consts.ADVANCED_COMPUTER_SEARCH_XML_NAME,
                                           device_list_name=jamf_consts.ADVANCED_COMPUTER_SEARCH_DEVICE_LIST_NAME,
                                           headers=self.headers)
        if type(computers) == dict:
            computers = [computers]
        mobile_devices = self._get_jamf_devices(url=jamf_consts.ADVANCED_MOBILE_SEARCH_URL,
                                                data=jamf_consts.ADVANCED_MOBILE_SEARCH,
                                                xml_name=jamf_consts.ADVANCED_MOBILE_SEARCH_XML_NAME,
                                                device_list_name=jamf_consts.ADVANCED_MOBILE_SEARCH_DEVICE_LIST_NAME,
                                                headers=non_json_headers).get('mobile_device', [])
        if type(mobile_devices) == dict:
            mobile_devices = [mobile_devices]
        return computers + mobile_devices
