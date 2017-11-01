import pytest
import services.socket_service as socket_service
from services.simple_fixture import initalize_fixture


class CoreService(socket_service.SocketService):
    def __init__(self, endpoint, config_file_path):
        super().__init__(endpoint, config_file_path)


@pytest.fixture
def core_fixture(request):
    service = CoreService(('localhost', 80), '../plugins/core/docker-compose.yml')
    initalize_fixture(request, service)
    return service
