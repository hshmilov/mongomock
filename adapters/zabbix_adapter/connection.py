import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from zabbix_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class ZabbixConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json-rpc', 'Accept': 'application/json'}

    def _connect(self):
        _auth_json = self._post(consts.API_PATH, body_params={consts.JSON_RPC_KEY_NAME: consts.JSON_RPC_VALUE,
                                                              consts.METHOD_KEY_NAME: consts.LOGIN_METHOD_NAME,
                                                              consts.PARMAS_KEY_NAME:
                                                              {consts.USERNAME_KEY_NAME_IN_PARAMS: self._username,
                                                               consts.PASSWORD_KEY_NAME_IN_PARAMS: self._password},
                                                              consts.ID_KEY_NAME: consts.RANDOM_ID_LOGIN,
                                                              consts.AUTH_KEY_NAME: None})
        if consts.RESULT_ATTRIBUTE_NAME not in _auth_json:
            raise RESTException((_auth_json.get('error') or {}).get('data') or 'Invalid Params')
        self._auth = _auth_json[consts.RESULT_ATTRIBUTE_NAME]

    def get_device_list(self):
        apps_host_dict = dict()
        try:
            apps_raw = self._post(consts.API_PATH,
                                  body_params={consts.JSON_RPC_KEY_NAME: consts.JSON_RPC_VALUE,
                                               consts.METHOD_KEY_NAME: consts.GET_APPS_METHOD,
                                               consts.PARMAS_KEY_NAME:
                                                   {consts.OUTPUT_KEY_NAME_IN_PARAMS:
                                                    consts.EXTEND_VALUE_IN_PARAMS},
                                               consts.ID_KEY_NAME: consts.RANDOM_ID_APPS,
                                               consts.AUTH_KEY_NAME:
                                                   self._auth}
                                  )[consts.RESULT_ATTRIBUTE_NAME]
            for app_raw in apps_raw:
                if isinstance(app_raw, dict) and app_raw.get('hostid') and app_raw.get('name'):
                    if not apps_host_dict.get(app_raw.get('hostid')):
                        apps_host_dict[app_raw.get('hostid')] = []
                    apps_host_dict[app_raw.get('hostid')].append(app_raw.get('name'))
        except Exception:
            logger.exception(f'Problem getting Apps')
        for device_raw in self._post(consts.API_PATH, body_params={consts.JSON_RPC_KEY_NAME: consts.JSON_RPC_VALUE,
                                                                   consts.METHOD_KEY_NAME: consts.GET_HOSTS_METHOD,
                                                                   consts.PARMAS_KEY_NAME:
                                                                       {consts.OUTPUT_KEY_NAME_IN_PARAMS:
                                                                        consts.EXTEND_VALUE_IN_PARAMS,
                                                                        'selectInterfaces':
                                                                            consts.EXTEND_VALUE_IN_PARAMS,
                                                                        'selectInventory':
                                                                            consts.EXTEND_VALUE_IN_PARAMS},
                                                                   consts.ID_KEY_NAME: consts.RANDOM_ID_DEVICES,
                                                                   consts.AUTH_KEY_NAME:
                                                                       self._auth})[consts.RESULT_ATTRIBUTE_NAME]:
            yield device_raw, apps_host_dict
