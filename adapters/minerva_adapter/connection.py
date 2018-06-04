from axonius.clients.rest.connection import RESTConnection
from minerva_adapter import consts
import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.clients.rest.exception import RESTException


class MinervaConnection(RESTConnection):

    def _connect(self):
        if self._username is not None and self._password is not None:
            connection_dict = {'username': self._username,
                               'password': self._password}
            self._post("login", body_params=connection_dict)
        else:
            raise RESTException("No user name or password")

    def get_device_list(self):
        devices_list = self._post('endpoints', body_params={
            'page': {'index': '1', 'length': str(consts.DEVICES_PER_PAGE)}})
        if devices_list == []:
            return
        exception_in_fetch = 0
        yield from devices_list
        for page in range(1, consts.PAGES_MAX):
            try:
                devices_list = self._post('endpoints', body_params={'page': {'index': str(
                    page * consts.DEVICES_PER_PAGE), 'length': str(consts.DEVICES_PER_PAGE)}})
                if devices_list == []:
                    break
                exception_in_fetch = 0
                yield from devices_list
            except Exception:
                # stop after three bad pages
                if exception_in_fetch == 3:
                    break
                exception_in_fetch += 1
                logger.exception(f"Problem getting page {str(page)}")
