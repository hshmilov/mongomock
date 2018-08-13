import requests
import logging
logger = logging.getLogger(f'axonius.{__name__}')

from carbonblack_protection_adapter.exceptions import CarbonblackProtectionAlreadyConnected, CarbonblackProtectionConnectionError,\
    CarbonblackProtectionNotConnected, \
    CarbonblackProtectionRequestException


class CarbonblackProtectionConnection(object):
    def __init__(self, domain, verify_ssl, https_proxy):
        """ Initializes a connection to CarbonblackProtection using its rest API

        :param str domain: domain address for CarbonblackProtection
        """
        self.domain = domain
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url

        if not url.endswith('/'):
            url += '/'
        url += 'api/bit9platform/v1/'
        self.url = url
        self.session = None
        self.verify_ssl = verify_ssl
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        self.proxies = {}
        self.proxies['http'] = None
        if https_proxy is not None:
            self.proxies['https'] = https_proxy
        logger.info(f"Proxies: {self.proxies}")

    def set_credentials(self, apikey):
        """ Set the connection credentials

        :param str apikey: The username
        """
        self.apikey = apikey

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
            raise CarbonblackProtectionAlreadyConnected()
        session = requests.Session()
        if self.apikey is not None:
            self.headers['X-Auth-Token'] = self.apikey
            try:
                response = session.get(self._get_url_request('computer'), params={
                                       "offset": str(0), "limit": str(1)}, verify=self.verify_ssl,
                                       headers=self.headers, timeout=(5, 30), proxies=self.proxies)
                response.raise_for_status()
            except requests.HTTPError as e:
                raise CarbonblackProtectionConnectionError(str(e))
        else:
            raise CarbonblackProtectionConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _get(self, name, params=None):
        """ Serves a GET request to CarbonblackProtection API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise CarbonblackProtectionNotConnected()
        params = params or {}
        try:
            response = self.session.get(self._get_url_request(name), params=params,
                                        headers=self.headers, verify=self.verify_ssl, timeout=(5, 30), proxies=self.proxies)
            response.raise_for_status()
        except requests.HTTPError as e:
            raise CarbonblackProtectionRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses CarbonblackProtection's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        devices_list = []
        offset = 0
        raw_count = self._get('computer', params={"limit": str(-1)})
        total_count = raw_count["count"]
        logger.debug(f"CarbonBlack protection API Returned a count of {total_count} devices")
        if total_count < 0:
            # Negetive total_count means the server can't evaluate the amout of devices.
            #  In such case we will query for a list 50,000 more device. The
            total_count *= -1
            total_count += 50000

        try:
            while offset <= total_count:
                logger.debug(f"Getting {offset} devices offset")
                devices_list += self._get('computer', params={"limit": str(1000), "offset": str(offset)})
                offset += 1000
        except Exception:
            logger.exception(f"Problem getting device in row number: {row_number}")
        return devices_list

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
