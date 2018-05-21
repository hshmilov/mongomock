import logging
logger = logging.getLogger(f"axonius.{__name__}")
import requests
import base64
from urllib3.util.url import parse_url


from blackberry_uem_adapter.exceptions import BlackberryUemAlreadyConnected, BlackberryUemConnectionError, BlackberryUemNotConnected, \
    BlackberryUemRequestException


class BlackberryUemConnection(object):
    def __init__(self, domain, verify_ssl, tenant_guid):
        """ Initializes a connection to BlackberryUem using its rest API

        :param str domain: domain address for BlackberryUem
        :param bool verify_ssl Verify the ssl
        """
        self.domain = domain
        self.tenant_guid = tenant_guid
        url = parse_url(domain)
        self.url = f"https://{url.host}:18084/{self.tenant_guid}/api/v1/"
        self.session = None
        self.username = None
        self.password = None
        self.username_domain = None
        self.verify_ssl = verify_ssl
        self.headers = {}

    def set_credentials(self, username, password, username_domain):
        """ Set the connection credentials

        :param str username: The username
        :param str password: The password
        """
        self.username = username
        self.password = password
        self.username_domain = username_domain

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
            raise BlackberryUemAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            auth_dict = {'username': self.username, 'password': base64.b64encode(
                bytearray(self.password, "utf-8")).decode("utf-8")}
            if self.username_domain is None:
                auth_dict['provider'] = "LOCAL"
            else:
                auth_dict["domain"] = self.username_domain
                auth_dict["provider"] = "AD"
            response = session.post(self._get_url_request('util/authorization'), json=auth_dict,
                                    headers={'Content-Type': "application/vnd.blackberry.authorizationrequest-v1+json"},
                                    verify=self.verify_ssl)
            try:
                response.raise_for_status()
                self.headers["Authorization"] = response.text
            except requests.HTTPError as e:
                raise BlackberryUemConnectionError(str(e))
        else:
            raise BlackberryUemConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _get(self, name, params=None, use_full_url=False):
        """ Serves a GET request to BlackberryUem API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise BlackberryUemNotConnected()
        params = params or {}
        if use_full_url == False:
            url = self._get_url_request(name)
        else:
            url = name
        response = self.session.get(url, params=params,
                                    headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise BlackberryUemRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses BlackberryUem's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        devices_raw = self._get('devices')["devices"]
        for device_raw in devices_raw:
            try:
                device_links = device_raw.get("links")
                for link in device_links:
                    if link["rel"] == "userDevice":
                        user_device_url = link["href"]
                device_raw["applications"] = self._get(
                    user_device_url + "/applications", use_full_url=True)["deviceApplications"]
            except Exception:
                logger.exception(f"Problem getting applications for device : {device_raw}")
        return devices_raw

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
