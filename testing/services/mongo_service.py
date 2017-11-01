import pytest
import services.socket_service as socket_service
from services.simple_fixture import initalize_fixture


class MongoService(socket_service.SocketService):
    def __init__(self, endpoint, config_file_path):
        super().__init__(endpoint, config_file_path)


@pytest.fixture
def mongo_fixture(request):
    service = MongoService(('localhost', 27018), '../devops/systemization/database/docker-compose.yml')
    initalize_fixture(request, service)
    return service
