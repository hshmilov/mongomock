import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from mobileiron_adapter import consts


class MobileironConnection(RESTConnection):
    def __init__(self, *args, fetch_apps: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.__fetch_apps = fetch_apps

    def _connect(self):
        if self._username is not None and self._password is not None:
            self._get('ping', do_basic_auth=True)
        else:
            raise RESTException("No user name or password")

    def get_device_list(self, **kwargs):
        device_space_id = self._get("device_spaces/mine")["results"][0]["id"]
        count = self._get(
            "devices/count", url_params={'adminDeviceSpaceId': device_space_id, 'query': ""})["totalCount"]
        fields_raw = self._get("devices/search_fields",
                               url_params={'adminDeviceSpaceId': device_space_id, 'query': ""})["results"]
        fields = "common.id,"
        for field_raw in fields_raw:
            fields += field_raw["name"] + ","
        fields = fields[:-1]
        offset = 0

        device_apps_requests_async = []
        device_apps_requests_devices_raw = []

        original_count = count
        while count > 0:
            try:
                logger.debug(f"Fetching devices {offset} to {offset+consts.DEVICE_PER_PAGE}")
                paged_devices_list = self._get("devices", url_params={'adminDeviceSpaceId': device_space_id, 'limit': consts.DEVICE_PER_PAGE,
                                                                      'offset': offset, 'query': "",
                                                                      'fields': fields,
                                                                      'sortOrder': 'ASC',
                                                                      'sortField': 'user.display_name'})["results"]
                if self.__fetch_apps:
                    for device_raw in paged_devices_list:
                        try:
                            device_uuid = device_raw.get("common.uuid")
                            if device_uuid is not None:
                                device_apps_requests_async.append(
                                    {
                                        "name": "devices/appinventory",
                                        "url_params":
                                            {'deviceUuids': str(device_uuid), 'adminDeviceSpaceId': device_space_id},
                                        "do_basic_auth": True
                                    }
                                )
                                device_apps_requests_devices_raw.append(device_raw)
                        except Exception:
                            logger.exception(f"Problem fetching apps of device {device_raw}, fetching without apps")
                            yield device_raw
                else:
                    for device_raw in paged_devices_list:
                        yield device_raw
            except Exception:
                logger.exception(f"Problem fetching devices at offset {offset}")
            count -= consts.DEVICE_PER_PAGE
            offset += consts.DEVICE_PER_PAGE

        # For those who have apps, we still haven't yielded them, lets do that.
        app_devices_count = 0
        for device_raw, device_apps_response in zip(device_apps_requests_devices_raw, self._async_get(device_apps_requests_async)):
            if self._is_async_response_good(device_apps_response):
                try:
                    app_devices_count += 1
                    device_raw["appInventory"] = device_apps_response["results"][0]["appInventory"]
                except Exception:
                    logger.exception(f"Exceptionw while parsing device apps from response {device_apps_response}, "
                                     f"device_raw is {device_raw}, yielding without apps")
            else:
                logger.error(f"Error getting apps for device, "
                             f"response is {device_apps_response} for device {device_raw}, yielding without apps")

            yield device_raw

        logger.info(f"Finished getting {original_count} mobileiron devices from server, "
                    f"Got apps for {app_devices_count} devices")
        return
