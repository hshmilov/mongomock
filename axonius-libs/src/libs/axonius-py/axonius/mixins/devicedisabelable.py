import logging
from abc import ABC, abstractmethod

from axonius.plugin_base import add_rule, return_error
from axonius.utils.entity_finder import EntityFinder
from axonius.utils.threading import LazyMultiLocker

from axonius.mixins.feature import Feature

logger = logging.getLogger(f'axonius.{__name__}')


class Devicedisabelable(Feature, ABC):
    """
    Define a common API for adapters that can "disable" or "enable" a device
    See https://axonius.atlassian.net/wiki/spaces/AX/pages/609878017/Adapters+that+can+disable+users+or+devices
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__lazy_lock = LazyMultiLocker()

    @add_rule('devices/enable', methods=["POST"])
    def enable_device(self):
        """
        Enables (un-disable) devices
        :return:
        """
        devices_ids = self.get_request_data_as_object()
        if not devices_ids:
            return return_error("Invalid devices ids given")
        logger.info(f"Enabling the following device IDs: {devices_ids}")
        err = ""
        for device_id in devices_ids:
            with self.__lazy_lock.get_lock([device_id]):
                try:
                    data, client = self.__entity_finder.get_data_and_client_data(device_id)
                except Exception as e:
                    logger.exception(f"{repr(e)}")
                    err += str(e) + "\n"
                else:
                    try:
                        self._enable_device(data, client)
                    except Exception as e:
                        logger.exception(f"{repr(e)}")
                        err += str(e) + "\n"

        return return_error(err, 500) if err else ""

    @add_rule('devices/disable', methods=["POST"])
    def disable_device(self):
        """
        Disable devices
        :return:
        """
        devices_ids = self.get_request_data_as_object()
        if not devices_ids:
            return return_error("Invalid devices ids given")
        logger.info(f"Disabeling the following device IDs: {devices_ids}")
        err = ""
        for device_id in devices_ids:
            with self.__lazy_lock.get_lock([device_id]):
                try:
                    data, client = self.__entity_finder.get_data_and_client_data(device_id)
                except Exception as e:
                    logger.exception(f"{repr(e)}")
                    err += str(e) + "\n"
                else:
                    try:
                        self._disable_device(data, client)
                    except Exception as e:
                        logger.exception(f"{repr(e)}")
                        err += str(e) + "\n"

        return return_error(err, 500) if err else ""

    @property
    def __entity_finder(self):
        return EntityFinder(self.devices_db, self._clients, self.plugin_unique_name)

    @abstractmethod
    def _enable_device(self, device_data, client_data):
        pass

    @abstractmethod
    def _disable_device(self, device_data, client_data):
        pass

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Devicedisabelable"]
