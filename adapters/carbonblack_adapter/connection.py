import requests
import logging
logger = logging.getLogger(f"axonius.{__name__}")

from carbonblack_adapter.exceptions import CarbonblackAlreadyConnected, CarbonblackConnectionError, CarbonblackNotConnected, \
    CarbonblackRequestException


class CarbonblackConnection(object):
    def __init__(self, domain, verify_ssl):
        """ Initializes a connection to Carbonblack using its rest API

        :param str domain: domain address for Carbonblack
        """
        self.domain = domain
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url

        if not url.endswith('/'):
            url += '/'
        url += 'integrationServices/v3/'
        self.url = url
        self.session = None
        self.verify_ssl = verify_ssl
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def set_credentials(self, apikey, connector_id):
        """ Set the connection credentials

        :param str apikey: The username
        :param str connector_id: The password
        """
        self.apikey = apikey
        self.connector_id = connector_id

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
            raise CarbonblackAlreadyConnected()
        session = requests.Session()
        if self.connector_id is not None and self.apikey is not None:
            self.headers['X-Auth-Token'] = self.apikey + "/" + self.connector_id
            response = session.get(self._get_url_request('device'), params={
                                   "rows": str(10), "start": str(1)}, verify=self.verify_ssl, headers=self.headers)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise CarbonblackConnectionError(str(e))
        else:
            raise CarbonblackConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _get(self, name, params=None):
        """ Serves a GET request to Carbonblack API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise CarbonblackNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params,
                                    headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise CarbonblackRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Carbonblack's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        devices_list = []
        row_number = 1
        raw_results = self._get('device', params={"rows": str(100), "start": str(row_number)})
        total_count = raw_results["totalResults"]
        devices_list += raw_results["results"]
        try:
            while row_number + 100 <= total_count:
                row_number += 100
            devices_list += self._get('device', params={"rows": str(100), "start": str(row_number)})["results"]
        except:
            logger.exception(f"Problem getting device in row number: {row_number}")
        return devices_list

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
