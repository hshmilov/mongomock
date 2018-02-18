import requests
import time
import xml.etree.cElementTree as ET

from axonius.utils.xml2json_parser import Xml2Json
from qualys_scans_adapter.exceptions import QualysScansConnectionError, QualysScansAPILimitException

"""
In this connection we target the VM module (and probably PC later on).
These modules have a rate limit - by default of 2 connections through api v2.0 or 300 api requests an hour.
For the sake of the user - if the next api request is allowed within the next 30 seconds we wait and try again.
"""


class QualysScansConnection(object):
    def __init__(self, logger, domain):
        """ Initializes a connection to qualys scans using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for qualys scans
        """
        self.logger = logger
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        self.url = url + 'api/2.0/fo/'
        self.headers = {'X-Requested-With': 'Axonius Qualys Scans Adapter'}
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
            self.logger.error(f"Username {0} or password {1} is None".format(
                self.auth[0], self.auth[1]))
            raise QualysScansConnectionError(f"Username {self.auth[0]} or password {self.auth[1]} is None")
        response = self.get("scan", auth=self.auth, headers=self.headers,
                            params=[('action', 'list'), ('launched_after_datetime', '3999-12-31T23:12:00Z')])
        response_tree = ET.fromstring(response.text)
        if response_tree.find('RESPONSE') is None or response_tree.find('RESPONSE').find('DATETIME') is None \
                or response_tree.find('RESPONSE').find('CODE') is not None:
            self.logger.error("Failed to connect to qualys scans.", response.text)
            raise QualysScansConnectionError(response.text)

    def __del__(self):
        self.logout()

    def logout(self):
        """ Logs out of the service"""
        self.close()

    def close(self):
        """ Closes the connection """

    def _qualys_api_request(self, request_func, url, retries=1, max_seconds=1, **kwargs):
        seconds_waited = 0
        for i in range(retries):
            try:
                response = request_func(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.HTTPError as e:
                if response.status_code == 409:  # conflict for url - reached the API limit
                    self.logger.warn('Qualys API limit reached. {0}'.format(str(e)), response.text, **kwargs)
                    error = Xml2Json(response.text).result
                    seconds_to_wait = int(error['SIMPLE_RETURN']['RESPONSE']['ITEM_LIST']['ITEM']['VALUE'])
                    if seconds_to_wait + seconds_waited < max_seconds:
                        seconds_waited += seconds_to_wait
                        time.sleep(seconds_to_wait)
                        continue
                    raise QualysScansAPILimitException(seconds_to_wait, f'Qualys API limit reached. {0}'.format(str(e)),
                                                       response.text, str(kwargs))
                else:
                    self.logger.exception('Qualys request exception. {0}'.format(str(e)), response.text, **kwargs)
                raise e

    def get(self, name, headers=None, auth=None, params=None):
        """ Serves a POST request to QualysScans API

        :param str name: the name of the page to request
        :param dict headers: the headers for the post request
        :param list params: the params
        :param tuple auth: the username and password
        :return: the service response or raises an exception if it's not 200
        """
        return self._qualys_api_request(requests.get, self._get_url_request(name), retries=3, max_seconds=30,
                                        headers=headers, auth=auth, params=params)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
