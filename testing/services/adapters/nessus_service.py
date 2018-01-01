import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture


class NessusService(plugin_service.AdapterService):
    def __init__(self, compose_file_path='../adapters/nessus-adapter/docker-compose.yml',
                 config_file_path='../adapters/nessus-adapter/src/plugin_config.ini',
                 container_name='nessus-adapter',
                 *vargs, **kwargs):
        super().__init__(compose_file_path, config_file_path, container_name, *vargs, **kwargs)


@pytest.fixture(scope="module", autouse=True)
def nessus_fixture(request):
    service = NessusService()
    initialize_fixture(request, service)
    return service
