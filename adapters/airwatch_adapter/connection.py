import logging
logger = logging.getLogger(f"axonius.{__name__}")

import requests
import xml.etree.ElementTree as ET


from airwatch_adapter.exceptions import AirwatchAlreadyConnected, AirwatchConnectionError, AirwatchNotConnected, \
    AirwatchRequestException


class AirwatchConnection(object):
    def __init__(self, domain, apikey, verify_ssl):
        """ Initializes a connection to Airwatch using its rest API

        :param str domain: domain address for Airwatch
        :param str apikey: API key of Airwatch
        :param bool verify_ssl
        """
        super().__init__()
        self.domain = domain
        self.apikey = apikey
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        url += 'api/'
        self.url = url
        self.session = None
        self.username = None
        self.password = None
        self.headers = None
        self.apikey = None
        self.verify_ssl = verify_ssl

    def set_credentials(self, username, password, apikey):
        """ Set the connection credentials

        :param str username: The username
        :param str password: The password
        :param str apikey: The API Key
        """
        self.username = username
        self.password = password
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
            raise AirwatchAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None and self.apikey is not None:
            self.headers = {"User-Agent": "Fiddler"}
            self.headers["aw-tenant-code"] = self.apikey
            self.headers["Accept"] = "application/xml"
            response = session.get(self._get_url_request('system/info'), headers=self.headers,
                                   auth=(self.username, self.password), verify=self.verify_ssl)
            self.headers["Accept"] = "application/json"
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise AirwatchConnectionError(str(e))
        else:
            raise AirwatchConnectionError("No user name or password or API key")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _get(self, name, params=None, use_full_path=False):
        """ Serves a GET request to Airwatch API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise AirwatchNotConnected()
        params = params or {}
        if use_full_path:
            full_url = name
        else:
            full_url = self._get_url_request(name)
        response = self.session.get(full_url, params=params, headers=self.headers,
                                    auth=(self.username, self.password), verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise AirwatchRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Airwatch's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        devices_raw_list = []
        devices_search_raw = self._get('/mdm/devices/search?pagesize=500&page=0')
        devices_raw_list += devices_search_raw.get("Devices", [])
        total_count = devices_search_raw.get("Total", 1)
        pages_count = 1
        while total_count > pages_count * 500:
            devices_search_raw = self._get('/mdm/devices/search?pagesize=500&page=' + str(pages_count))
            devices_raw_list += devices_search_raw.get("Devices", [])
            pages_count += 1

        for device_raw in devices_raw_list:
            device_id = device_raw.get("Id", {}).get("Value", 0)
            if device_id == 0:
                continue
            try:
                device_raw["Network"] = self._get('/mdm/devices/' + str(device_id) + '/network')
            except Exception:
                logger.exception("Problem fetching network")

            try:
                device_apps_list = []
                apps_search_raw = self._get('/mdm/devices/' + str(device_id) + '/apps?pagesize=500&page=0')
                device_apps_list += apps_search_raw.get("DeviceApps", [])
                total_count = devices_search_raw.get("Total", 1)
                pages_count = 1
                while total_count > pages_count * 500:
                    apps_search_raw = self._get('/mdm/devices/' + str(device_id) +
                                                '/apps?pagesize=500&page=' + str(pages_count))
                    device_apps_list += apps_search_raw.get("DeviceApps", [])
                    pages_count += 1
                device_raw["DeviceApps"] = device_apps_list
            except Exception:
                logger.exception("Problem fetching apps")
        return devices_raw_list

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
