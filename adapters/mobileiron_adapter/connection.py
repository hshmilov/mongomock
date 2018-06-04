import logging
logger = logging.getLogger(f"axonius.{__name__}")
import requests

from mobileiron_adapter.exceptions import MobileironAlreadyConnected, MobileironConnectionError, MobileironNotConnected, \
    MobileironRequestException


class MobileironConnection(object):
    def __init__(self, domain, verify_ssl, fetch_apps):
        """ Initializes a connection to Mobileiron using its rest API

        :param str domain: domain address for Mobileiron
        :param bool verify_ssl Verify the ssl
        :param bool fetch_apps A bool to decide if we want to fetch apps which is very slow
        """
        self.domain = domain
        url = domain
        if not url.endswith('/'):
            url += '/'
        url += 'rest/api/v2/'
        self.url = url
        self.session = None
        self.username = None
        self.password = None
        self.verify_ssl = verify_ssl
        self.fetch_apps = fetch_apps
        self.headers = {'Content-Type': 'application/json'}

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
            raise MobileironAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            try:
                response = session.get(self._get_url_request('ping'), auth=(
                    self.username, self.password), verify=self.verify_ssl, timeout=(5, 30))
                response.raise_for_status()
            except requests.HTTPError as e:
                raise MobileironConnectionError(str(e))
        else:
            raise MobileironConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _get(self, name, params=None):
        """ Serves a GET request to Mobileiron API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise MobileironNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params,
                                    headers=self.headers, auth=(self.username, self.password), verify=self.verify_ssl, timeout=(5, 30))
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise MobileironRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Mobileiron's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        device_space_id = self._get("device_spaces/mine")["results"][0]["id"]
        count = self._get("devices/count", params={'adminDeviceSpaceId': device_space_id, 'query': ""})["totalCount"]
        fields_raw = self._get("devices/search_fields",
                               params={'adminDeviceSpaceId': device_space_id, 'query': ""})["results"]
        fields = "common.id,"
        for field_raw in fields_raw:
            fields += field_raw["name"] + ","
        fields = fields[:-1]
        offset = 0
        while count > 0:
            try:
                logger.debug(f"Fetching devices {offset} to {offset+200}")
                paged_devices_list = self._get("devices", params={'adminDeviceSpaceId': device_space_id, 'limit': 200,
                                                                  'count': 50, 'offset': offset, 'query': "",
                                                                  'fields': fields,
                                                                  'sortOrder': 'ASC',
                                                                  'sortField': 'user.display_name'})["results"]
                if self.fetch_apps:
                    app_devices_count = 0
                    for device_raw in paged_devices_list:
                        try:
                            app_devices_count += 1
                            if app_devices_count % 100 == 0:
                                logger.debug(f"Got apps for {app_devices_count} devices")
                            device_uuid = device_raw.get("common.uuid")
                            if device_uuid is not None:
                                device_raw["appInventory"] = self._get("devices/appinventory",
                                                                       params={'deviceUuids': str(device_uuid), 'adminDeviceSpaceId': device_space_id})["results"][0]["appInventory"]
                        except Exception:
                            logger.exception(f"Problem fetching apps of device {device_raw}")
                        yield device_raw
                else:
                    for device_raw in paged_devices_list:
                        yield device_raw
            except Exception:
                logger.exception(f"Problem fetching devices at offset {offset}")
            count -= 200
            offset += 200
        return

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
