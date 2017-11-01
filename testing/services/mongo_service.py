import pytest
import pymongo

import services.compose_service
from services.simple_fixture import initalize_fixture


class MongoService(services.compose_service.ComposeService):
    def __init__(self, endpoint, config_file_path):
        super().__init__(config_file_path)
        self.endpoint = endpoint

    @staticmethod
    def is_mongo_alive(endpoint):
        try:
            client = pymongo.MongoClient(endpoint[0], endpoint[1], serverSelectionTimeoutMS=0)
            client.server_info()
            return True
        except Exception as err:
            print(err)
            return False

    def is_up(self):
        return self.is_mongo_alive(self.endpoint)


@pytest.fixture
def mongo_fixture(request):
    service = MongoService(('localhost', 27018), '../devops/systemization/database/docker-compose.yml')
    initalize_fixture(request, service)
    return service
