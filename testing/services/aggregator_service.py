import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initalize_fixture


class AggregatorService(plugin_service.PluginService):
    def __init__(self, compose_file_path='../plugins/aggregator-plugin/docker-compose.yml',
                 config_file_path='../plugins/aggregator-plugin/src/plugin_config.ini'):
        super().__init__(compose_file_path, config_file_path=config_file_path)


@pytest.fixture(scope="session")
def aggregator_fixture(request):
    service = AggregatorService()
    initalize_fixture(request, service)
    return service
