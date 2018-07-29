import logging
logger = logging.getLogger(f"axonius.{__name__}")
import requests
import base64
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException


class BlackberryUemConnection(RESTConnection):
    def __init__(self, *args, username_domain: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._username_domain = username_domain

    def _connect(self):
        if self._username is not None and self._password is not None:
            auth_dict = {'username': self._username, 'password': base64.b64encode(
                bytearray(self._password, "utf-8")).decode("utf-8")}
            if self._username_domain is None:
                auth_dict['provider'] = "LOCAL"
            else:
                auth_dict["domain"] = self._username_domain
                auth_dict["provider"] = "AD"
            try:
                response = self._session.post(self._get_url_request('util/authorization'), json=auth_dict,
                                              headers={
                    'Content-Type': "application/vnd.blackberry.authorizationrequest-v1+json"},
                    verify=self._verify_ssl, timeout=self._session_timeout, proxies=self._proxies)
                response.raise_for_status()
                self._session_headers["Authorization"] = response.text
                self._get('devices')
            except requests.HTTPError as e:
                raise RESTException(str(e))
        else:
            raise RESTException("No user name or password")

    def get_device_list(self):
        devices_raw = self._get('devices')["devices"]
        for device_raw in devices_raw:
            try:
                device_links = device_raw.get("links")
                for link in device_links:
                    if link["rel"] == "userDevice":
                        user_device_url = link["href"]
                device_raw["applications"] = self._get(
                    user_device_url + "/applications", force_full_url=True)["deviceApplications"]
            except Exception:
                logger.exception(f"Problem getting applications for device : {device_raw}")
            yield device_raw
