import pytest
import requests
import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture


class CoreService(plugin_service.PluginService):
    def __init__(self, compose_file_path='../plugins/core/docker-compose.yml',
                 config_file_path='../plugins/core/src/plugin_config.ini',
                 container_name='core'):
        super().__init__(compose_file_path, config_file_path, container_name)

    def register(self, api_key=None, plugin_name=""):
        headers = {}
        params = {}
        if api_key:
            headers[plugin_service.API_KEY_HEADER] = api_key
            params[plugin_service.UNIQUE_KEY_PARAM] = plugin_name

        return requests.get(self.req_url + "/register", headers=headers, params=params)

    def _is_service_alive(self):
        try:
            r = self.version()
            return r.status_code == 200
        except:
            return False

    @pytest.fixture(scope="module")
    def core_fixture(request):
        service = CoreService()
        initialize_fixture(request, service)
        return service
