import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture


class AdService(plugin_service.AdapterService):
    def __init__(self, compose_file_path='../adapters/ad-adapter/docker-compose.yml',
                 config_file_path='../adapters/ad-adapter/src/plugin_config.ini',
                 container_name="ad-adapter"):
        super().__init__(compose_file_path, config_file_path, container_name)


@pytest.fixture(scope="module")
def ad_fixture(request):
    service = AdService()
    initialize_fixture(request, service)
    return service
