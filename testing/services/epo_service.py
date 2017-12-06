import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture


class EpoService(plugin_service.AdapterService):
    def __init__(self, compose_file_path='../adapters/epo-adapter/docker-compose.yml',
                 config_file_path='../adapters/epo-adapter/src/plugin_config.ini',
                 container_name='epo-adapter'):
        super().__init__(compose_file_path, config_file_path, container_name)


@pytest.fixture(scope="module")
def epo_fixture(request):
    service = EpoService()
    initialize_fixture(request, service)
    return service
