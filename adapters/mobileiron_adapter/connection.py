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
        while count > 0:
            try:
                logger.debug(f"Fetching devices {offset} to {offset+consts.DEVICE_PER_PAGE}")
                paged_devices_list = self._get("devices", url_params={'adminDeviceSpaceId': device_space_id, 'limit': consts.DEVICE_PER_PAGE,
                                                                      'offset': offset, 'query': "",
                                                                      'fields': fields,
                                                                      'sortOrder': 'ASC',
                                                                      'sortField': 'user.display_name'})["results"]
                if self.__fetch_apps:
                    app_devices_count = 0
                    for device_raw in paged_devices_list:
                        try:
                            app_devices_count += 1
                            if app_devices_count % 100 == 0:
                                logger.debug(f"Got apps for {app_devices_count} devices")
                            device_uuid = device_raw.get("common.uuid")
                            if device_uuid is not None:
                                device_raw["appInventory"] = self._get("devices/appinventory",
                                                                       url_params={'deviceUuids': str(device_uuid), 'adminDeviceSpaceId': device_space_id})["results"][0]["appInventory"]
                        except Exception:
                            logger.exception(f"Problem fetching apps of device {device_raw}")
                        yield device_raw
                else:
                    for device_raw in paged_devices_list:
                        yield device_raw
            except Exception:
                logger.exception(f"Problem fetching devices at offset {offset}")
            count -= consts.DEVICE_PER_PAGE
            offset += consts.DEVICE_PER_PAGE
        return
