import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initalize_fixture
from services.plugin_service import API_KEY_HEADER
import requests


class AggregatorService(plugin_service.PluginService):
    def __init__(self, compose_file_path='../plugins/aggregator-plugin/docker-compose.yml',
                 config_file_path='../plugins/aggregator-plugin/src/plugin_config.ini',
                 vol_config_file_path='../plugins/aggregator-plugin/src/plugin_volatile_config.ini'):
        super().__init__(compose_file_path, config_file_path, vol_config_file_path)

    def query_devices(self):
        response = requests.post(
            self.req_url + "/query_devices", headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200
        return response


@pytest.fixture(scope="module")
def aggregator_fixture(request):
    service = AggregatorService()
    initalize_fixture(request, service)
    return service
