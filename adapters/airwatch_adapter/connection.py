from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
import logging
logger = logging.getLogger(f'axonius.{__name__}')
from airwatch_adapter import consts


class AirwatchConnection(RESTConnection):

    def _connect(self):
        if self._username is not None and self._password is not None:
            # Note that the following self._get will have the application/xml Accept type,
            # but only afterwards we will update session headers to application/json.
            # when having both "Accept" in permanent and session headers, session wins.
            self._get("system/info", do_basic_auth=True, use_json_in_response=False)
            self._session_headers["Accept"] = "application/json"
        else:
            raise RESTException("No user name or password or API key")

    def get_device_list(self):
        devices_raw_list = []
        devices_search_raw = self._get(
            "mdm/devices/search", url_params={"pagesize": consts.PAGE_SIZE, "page": 0}, do_basic_auth=True)
        devices_raw_list += devices_search_raw.get("Devices", [])
        total_count = min(devices_search_raw.get("Total", 1), consts.MAX_DEVICES_NUMBER)
        pages_count = 1
        while total_count > pages_count * consts.PAGE_SIZE:
            try:
                devices_search_raw = self._get(
                    "mdm/devices/search", url_params={"pagesize": consts.PAGE_SIZE, "page": pages_count}, do_basic_auth=True)
                devices_raw_list += devices_search_raw.get("Devices", [])
            except Exception:
                logger.exception(f"Got problem fetching page {pages_count}")
            pages_count += 1

        for device_raw in devices_raw_list:
            try:
                device_id = device_raw.get("Id", {}).get("Value", 0)
                if device_id == 0:
                    logger.exception(f"No id for device {device_raw}")
                    continue
            except Exception:
                logger.exception(f"Problem getting id for {device_raw}")
                continue
            try:
                device_raw["Network"] = self._get(f"mdm/devices/{str(device_id)}/network", do_basic_auth=True)
            except Exception:
                logger.exception(f"Problem fetching network for {device_raw}")
            try:
                device_apps_list = []
                apps_search_raw = self._get(
                    f"mdm/devices/{str(device_id)}/apps", url_params={"pagesize": consts.PAGE_SIZE, "page": 0},
                    do_basic_auth=True)
                device_apps_list += apps_search_raw.get("DeviceApps", [])
                total_count = min(apps_search_raw.get("Total", 1), consts.MAX_APPS_NUMBER)
                pages_count = 1
                while total_count > pages_count * consts.PAGE_SIZE:
                    try:
                        apps_search_raw = self._get(
                            f"mdm/devices/{str(device_id)}/apps", url_params={"pagesize": consts.PAGE_SIZE,
                                                                              "page": pages_count}, do_basic_auth=True)
                        device_apps_list += apps_search_raw.get("DeviceApps", [])
                    except Exception:
                        logger.exception(f"Got problem fetching app for {device_raw} in page {pages_count}")
                    pages_count += 1
                device_raw["DeviceApps"] = device_apps_list
            except Exception:
                logger.exception(f"Problem fetching apps for {device_raw}")
            yield device_raw
