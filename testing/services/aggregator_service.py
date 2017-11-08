import pytest
import services.socket_service as socket_service
from services.simple_fixture import initalize_fixture


class AggregatorService(socket_service.SocketService):
    def __init__(self, compose_file_path='../plugins/aggregator-plugin/docker-compose.yml'):
        super().__init__(compose_file_path)


@pytest.fixture(scope="module")
def aggregator_fixture(request):
    service = AggregatorService()
    initalize_fixture(request, service)
    return service
