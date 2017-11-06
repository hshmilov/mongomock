import pytest
import services.socket_service as socket_service
from services.simple_fixture import initalize_fixture


class CoreService(socket_service.SocketService):
    def __init__(self, endpoint=('localhost', 80), config_file_path='../plugins/core/docker-compose.yml'):
        super().__init__(endpoint, config_file_path)


@pytest.fixture(scope="module")
def core_fixture(request):
    service = CoreService()
    initalize_fixture(request, service)
    return service
