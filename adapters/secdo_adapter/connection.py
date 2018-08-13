import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException


class SecdoConnection(RESTConnection):

    def __init__(self, *args, company: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._company = company

    def _connect(self):
        if self._company is not None and self._apikey is not None:
            try:
                self.__connection_dict = {'company': self._company}
                self._post("publicapiv2/run/command/", body_params=self.__connection_dict)
                api_version = "v2"
            except Exception as e2:
                try:
                    self.__connection_dict = {'company': self._company, 'apikey': self._apikey}
                    self._post("publicapi/agentmgmt/get/agents/", body_params=self.__connection_dict)
                    api_version = "v1"
                except Exception as e1:
                    raise RESTException(f"Error connecting to server: v2 - {str(e2), v1 - {str(e1)}}")
            self._api_version = api_version

        else:
            raise RESTException("No company or apikey")

    def get_device_list(self):
        if self._api_version == "v2":
            yield from self._post("publicapiv2/run/command/", body_params=self.__connection_dict)["agents"]
        else:
            yield from self._post("publicapi/agentmgmt/get/agents/", body_params=self.__connection_dict)["agents"]
