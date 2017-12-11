import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture


class EsxService(plugin_service.AdapterService):
    def __init__(self, compose_file_path='../adapters/esx-adapter/docker-compose.yml',
                 config_file_path='../adapters/esx-adapter/src/plugin_config.ini',
                 container_name='esx-adapter'):
        super().__init__(compose_file_path, config_file_path, container_name)


@pytest.fixture(scope="module")
def esx_fixture(request):
    service = EsxService()
    initialize_fixture(request, service)
    return service
