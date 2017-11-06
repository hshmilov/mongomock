import pytest
import pymongo

import services.compose_service
from services.simple_fixture import initalize_fixture


class MongoService(services.compose_service.ComposeService):
    def __init__(self, endpoint=('localhost', 27018),
                 config_file_path='../devops/systemization/database/docker-compose.yml'):
        super().__init__(config_file_path)
        self.endpoint = endpoint

    @staticmethod
    def is_mongo_alive(endpoint):
        try:
            client = pymongo.MongoClient(endpoint[0], endpoint[1])
            client.server_info()
            print("Mongo connection worked")
            return True
        except Exception as err:
            print(err)
            return False

    def is_up(self):
        return self.is_mongo_alive(self.endpoint)


@pytest.fixture(scope="module")
def mongo_fixture(request):
    service = MongoService()
    initalize_fixture(request, service)
    return service
