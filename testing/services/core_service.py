import pytest
import requests
import services.plugin_service as plugin_service
from services.simple_fixture import initalize_fixture


class CoreService(plugin_service.PluginService):
    def __init__(self, compose_file_path='../plugins/core/docker-compose.yml',
                 config_file_path='../plugins/core/src/plugin_config.ini',
                 vol_config_file_path='../adapters/core/src/plugin_volatile_config.ini'):
        super().__init__(compose_file_path, config_file_path, vol_config_file_path)

    def register(self, api_key=None):
        headers = {}
        if not api_key:
            headers[plugin_service.API_KEY_HEADER] = api_key

        return requests.get(self.req_url + "/register", headers=headers)

    @pytest.fixture(scope="session")
    def core_fixture(request):
        service = CoreService()
        initalize_fixture(request, service)
        return service
