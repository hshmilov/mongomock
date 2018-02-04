import requests

from services.plugin_service import PluginService, API_KEY_HEADER, UNIQUE_KEY_PARAM


class CoreService(PluginService):
    def __init__(self):
        super().__init__('core', service_dir='../plugins/core')

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
        except:
            return False

    def get_registered_plugins(self):
        return self.register()
