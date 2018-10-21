import logging

from axonius.clients.rest.connection import RESTConnection
from zabbix_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class ZabbixConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json-rpc', 'Accept': 'application/json'}

    def _connect(self):
        self._auth = self._post(consts.API_PATH, body_params={consts.JSON_RPC_KEY_NAME: consts.JSON_RPC_VALUE,
                                                              consts.METHOD_KEY_NAME: consts.LOGIN_METHOD_NAME,
                                                              consts.PARMAS_KEY_NAME:
                                                              {consts.USERNAME_KEY_NAME_IN_PARAMS: self._username,
                                                               consts.PASSWORD_KEY_NAME_IN_PARAMS: self._password},
                                                              consts.ID_KEY_NAME: consts.RANDOM_ID_LOGIN,
                                                              consts.AUTH_KEY_NAME: None})[consts.RESULT_ATTRIBUTE_NAME]

    def get_device_list(self):
        # I think these two shouldn't be consts because they are the only thing which is super specific to getHosts
        yield from self._post(consts.API_PATH, body_params={consts.JSON_RPC_KEY_NAME: consts.JSON_RPC_VALUE,
                                                            consts.METHOD_KEY_NAME: consts.GET_HOSTS_METHOD,
                                                            consts.PARMAS_KEY_NAME: {consts.OUTPUT_KEY_NAME_IN_PARAMS:
                                                                                     consts.EXTEND_VALUE_IN_PARAMS,
                                                                                     'selectInterfaces':
                                                                                     consts.EXTEND_VALUE_IN_PARAMS,
                                                                                     'selectInventory':
                                                                                     consts.EXTEND_VALUE_IN_PARAMS},
                                                            consts.ID_KEY_NAME: consts.RANDOM_ID_DEVICES,
                                                            consts.AUTH_KEY_NAME:
                                                                self._auth})[consts.RESULT_ATTRIBUTE_NAME]
