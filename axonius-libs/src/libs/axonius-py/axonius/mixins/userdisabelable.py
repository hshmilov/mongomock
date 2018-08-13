import logging
from abc import ABC, abstractmethod

from axonius.plugin_base import add_rule, return_error
from axonius.utils.entity_finder import EntityFinder
from axonius.utils.threading import LazyMultiLocker

from axonius.mixins.feature import Feature

logger = logging.getLogger(f'axonius.{__name__}')


class Userdisabelable(Feature, ABC):
    """
    Define a common API for adapters that can "disable" or "enable" a user
    See https://axonius.atlassian.net/wiki/spaces/AX/pages/609878017/Adapters+that+can+disable+users+or+devices
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__lazy_lock = LazyMultiLocker()

    @add_rule('users/enable', methods=["POST"])
    def enable_user(self):
        """
        Enables (un-disable) users
        :return:
        """
        users_ids = self.get_request_data_as_object()
        if not users_ids:
            return return_error("Invalid users ids given")
        logger.info(f"Enabling the following user IDs: {users_ids}")
        err = ""
        for user_id in users_ids:
            with self.__lazy_lock.get_lock([user_id]):
                try:
                    data, client = self.__entity_finder.get_data_and_client_data(user_id)
                except Exception as e:
                    logger.exception(f"{repr(e)}")
                    err += str(e) + "\n"
                else:
                    try:
                        self._enable_user(data, client)
                    except Exception as e:
                        logger.exception(f"{repr(e)}")
                        err += str(e) + "\n"

        return return_error(err, 500) if err else ""

    @add_rule('users/disable', methods=["POST"])
    def disable_user(self):
        """
        Disables users
        :return:
        """
        users_ids = self.get_request_data_as_object()
        if not users_ids:
            return return_error("Invalid users ids given")
        logger.info(f"Disabling the following user IDs: {users_ids}")
        err = ""
        for user_id in users_ids:
            with self.__lazy_lock.get_lock([user_id]):
                try:
                    data, client = self.__entity_finder.get_data_and_client_data(user_id)
                except Exception as e:
                    logger.exception(f"{repr(e)}")
                    err += str(e) + "\n"
                else:
                    try:
                        self._disable_user(data, client)
                    except Exception as e:
                        logger.exception(f"{repr(e)}")
                        err += str(e) + "\n"

        return return_error(err, 500) if err else ""

    @property
    def __entity_finder(self):
        return EntityFinder(self.users_db, self._clients, self.plugin_unique_name)

    @abstractmethod
    def _enable_user(self, user_data, client_data):
        pass

    @abstractmethod
    def _disable_user(self, user_data, client_data):
        pass

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["Userdisabelable"]
