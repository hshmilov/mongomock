import pytest
import services.socket_service as socket_service
from services.simple_fixture import initalize_fixture


class AggregatorService(socket_service.SocketService):
    def __init__(self, endpoint, config_file_path):
        super().__init__(endpoint, config_file_path)


@pytest.fixture
def aggregator_fixture(request):
    service = AggregatorService(('localhost', 5000), '../plugins/aggregator-plugin/docker-compose.yml')
    initalize_fixture(request, service)
    return service
