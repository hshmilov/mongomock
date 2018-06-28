from axonius.clients.rest.connection import RESTConnection
from fireeye_hx_adapter import consts
import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.clients.rest.exception import RESTException


class FireeyeHxConnection(RESTConnection):

    def _connect(self):
        if self._username is not None and self._password is not None:
            response = self._get('token', do_basic_auth=True, return_response_raw=True, use_json_in_response=False)
            self._session_headers["X-FeApi-Token"] = response.headers["X-FeApi-Token"]
        else:
            raise RESTException("No user name or password")

    def get_device_list(self):
        device_list_response = self._get('hosts', url_params={'offset': 0, 'limit': consts.DEVICES_PER_PAGE})
        devices_count = device_list_response["data"]["total"]
        yield from device_list_response["data"]["entries"]
        offset = consts.DEVICES_PER_PAGE
        while offset < devices_count:
            try:
                yield from self._get('hosts', url_params={'offset': offset, 'limit': consts.DEVICES_PER_PAGE})["data"]["entries"]
            except Exception:
                logger.exception(f"Problem getting offset {offset}")
            offset += consts.DEVICES_PER_PAGE
