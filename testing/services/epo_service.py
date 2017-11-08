import pytest
import services.socket_service as socket_service
from services.simple_fixture import initalize_fixture


class EpoService(socket_service.SocketService):
    def __init__(self, compose_file_path='../adapters/epo-adapter/docker-compose.yml'):
        super().__init__(compose_file_path)


@pytest.fixture(scope="module")
def epo_fixture(request):
    service = EpoService()
    initalize_fixture(request, service)
    return service
