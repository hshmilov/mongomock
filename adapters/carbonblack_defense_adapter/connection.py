import requests
import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection


class CarbonblackDefenseConnection(RESTConnection):

    def _connect(self):
        self._get("device")

    def get_device_list(self):
        row_number = 1
        raw_results = self._get('device', url_params={"rows": str(100), "start": str(row_number)})
        total_count = raw_results["totalResults"]
        logger.debug(f"Carbonblack Defense API returned a count of {total_count} devices")
        devices_list = raw_results["results"]
        for device_raw in devices_list:
            yield device_raw
        try:
            while row_number + 100 <= total_count:
                row_number += 100
                logger.debug(f"Getting {row_number} row number")
                devices_list = self._get('device', url_params={"rows": str(100), "start": str(row_number)})["results"]
                for device_raw in devices_list:
                    yield device_raw
        except Exception:
            logger.exception(f"Problem getting device in row number: {row_number}")
