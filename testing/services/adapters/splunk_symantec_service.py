import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture


class SplunkSymantecService(plugin_service.AdapterService):
    def __init__(self, compose_file_path='../adapters/splunk-symantec-adapter/docker-compose.yml',
                 config_file_path='../adapters/splunk-symantec-adapter/src/plugin_config.ini',
                 container_name='splunk-symantec-adapter',
                 *vargs, **kwargs):
        super().__init__(compose_file_path, config_file_path, container_name, *vargs, **kwargs)


@pytest.fixture(scope="module", autouse=True)
def splunk_symanctec_fixture(request):
    service = SplunkSymantecService()
    initialize_fixture(request, service)
    return service
