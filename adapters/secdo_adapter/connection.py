import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException


class SecdoConnection(RESTConnection):

    def __init__(self, *args, company: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._company = company
        self.__connection_dict = {'company': company}

    def _connect(self):
        if self._company is not None and self._apikey is not None:
            self._post("", body_params=self.__connection_dict)

        else:
            raise RESTException("No company or apikey")

    def get_device_list(self):
        yield from self._post("", body_params=self.__connection_dict)["agents"]
