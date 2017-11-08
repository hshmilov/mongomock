import pytest
import services.socket_service as socket_service
from services.simple_fixture import initalize_fixture


class AdService(socket_service.SocketService):
    def __init__(self, compose_file_path):
        super().__init__(compose_file_path)


@pytest.fixture(scope="module")
def ad_fixture(request):
    service = AdService('../adapters/ad-adapter/docker-compose.yml')
    initalize_fixture(request, service)
    return service
