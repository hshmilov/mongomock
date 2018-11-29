import requests

from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS_COLLECTION
from axonius.consts.core_consts import CORE_CONFIG_NAME
from services.plugin_service import PluginService, API_KEY_HEADER, UNIQUE_KEY_PARAM


class CoreService(PluginService):
    def __init__(self):
        super().__init__('core')

    def register(self, api_key=None, plugin_name=""):
        headers = {}
        params = {}
        if api_key:
            headers[API_KEY_HEADER] = api_key
            params[UNIQUE_KEY_PARAM] = plugin_name

        return requests.get(self.req_url + "/register", headers=headers, params=params)

    def _is_service_alive(self):
        try:
            r = self.version()
            return r.status_code == 200
        except Exception:
            return False

    def get_registered_plugins(self):
        return self.register()

    def set_config(self, config):
        self.db.get_collection('core', CONFIGURABLE_CONFIGS_COLLECTION).update_one(
            {'config_name': CORE_CONFIG_NAME},
            {'$set': config}
        )
        self.post('update_config')

    def set_execution_config(self, enabled):
        return self.set_config({'config.execution_settings.enabled': enabled})
