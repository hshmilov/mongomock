import logging
logger = logging.getLogger(f"axonius.{__name__}")
import requests

from qualys_adapter.exceptions import QualysConnectionError

"""
In this connection we target the Asset Management module of Qualys.
This module doesn't currently (28/1/2018) have a rate limit as oppose to the VM and PC modules.
Which is obviously why there's no regard to rate limiting
"""


class QualysConnection(object):
    def __init__(self, domain):
        """ Initializes a connection to Qualys using its rest API

        :param str domain: domain address for Qualys
        """
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        self.url = url + 'qps/rest/2.0/'
        self.headers = {'Accept': 'application/json'}
        self.auth = (None, None)

    def set_credentials(self, username, password):
        """ Set the connection credentials

        :param str username: The username
        :param str password: The password
        """
        self.auth = (username, password)

    def _get_url_request(self, request_name):
        """ Builds and returns the full url for the request

        :param request_name: the request name
        :return: the full request url
        """
        return self.url + request_name

    def connect(self):
        """ Connects to the service """

        if self.auth[0] is None or self.auth[1] is None:
            logger.error(f"Username {0} or password {1} is None".format(
                self.auth[0], self.auth[1]))
            raise QualysConnectionError(f"Username {self.auth[0]} or password {self.auth[1]} is None")
        response = self._post("count/am/hostasset/", auth=self.auth, headers=self.headers)

        if "SUCCESS" != response['responseCode']:
            logger.error("Failed to connect to qualys.", response["responseErrorDetails"])
            raise QualysConnectionError(response["responseErrorDetails"])

    def __del__(self):
        self.logout()

    def logout(self):
        """ Logs out of the service"""
        self.close()

    def close(self):
        """ Closes the connection """

    def _post(self, name, headers=None, cookies=None, auth=None, data=None):
        """ Serves a POST request to Qualys API

        :param str name: the name of the page to request
        :param dict headers: the headers for the post request
        :param dict cookies: the cookies - future compatibility for API 2.0
        :param tuple auth: the username and password
        :param str data: the body of the request
        :return: the service response or raises an exception if it's not 200
        """
        response = requests.post(self._get_url_request(name), headers=headers, cookies=cookies, auth=auth, data=data)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.exception('Post request failed. {0}'.format(str(e)), name, headers, cookies, auth, data)
            raise e
        response = response.json()
        return response['ServiceResponse']

    def get_device_iterator(self, data=None):
        """ Returns a list of all agents

        :param str data: the body of the request
        :return: the response
        :rtype: dict
        """
        return self._post("search/am/hostasset/", auth=self.auth, headers=self.headers, data=data)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
