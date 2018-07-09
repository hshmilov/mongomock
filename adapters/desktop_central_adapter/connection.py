import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection
from desktop_central_adapter import consts
import base64


class DesktopCentralConnection(RESTConnection):
    def __init__(self, *args, username_domain: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._username_domain = username_domain

    def _connect(self):
        if self._username is not None and self._password is not None:
            connection_dict = {'username': self._username,
                               'password': str(base64.b64encode(bytes(self._password, "utf-8")), encoding="utf-8")}
            if self._username_domain is None:
                connection_dict["auth_type"] = consts.LOCAL_AUTHENTICATION
            else:
                connection_dict["auth_type"] = consts.DOMAIN_AUTHENTICATION
                connection_dict["domainName"] = self._username_domain

            response = self._post("desktop/authentication", body_params=connection_dict)
            if (('message_response' not in response or 'status' not in response or 'message_version' not in response or
                 'message_version' not in response) or (response['status'] != 'success')):
                raise RESTException(f"Unknown connection error in authentication {str(response)}")
            self._session_headers["Authorization"] = response["message_response"]["authentication"]["auth_data"][
                "auth_token"]
        else:
            raise RESTException("No username or password")

    def get_device_list(self):
        yield from self._get(f"som/computers")["message_response"]["computers"]
