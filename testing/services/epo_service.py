import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initalize_fixture


class EpoService(plugin_service.AdapterService):
    def __init__(self, compose_file_path='../adapters/epo-adapter/docker-compose.yml',
                 config_file_path='../adapters/epo-adapter/src/plugin_config.ini',
                 vol_config_file_path='../adapters/epo-adapter/src/plugin_volatile_config.ini'):
        super().__init__(compose_file_path, config_file_path, vol_config_file_path)


@pytest.fixture(scope="module")
def epo_fixture(request):
    service = EpoService()
    initalize_fixture(request, service)
    return service
