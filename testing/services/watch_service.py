import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initalize_fixture


class WatchService(plugin_service.PluginService):
    def __init__(self, endpoint=('localhost', 5002), config_file_path='../plugins/watch-service/docker-compose.yml'):
        super().__init__(endpoint, config_file_path)


@pytest.fixture(scope="module")
def watch_fixture(request):
    service = WatchService()
    initalize_fixture(request, service)
    return service
