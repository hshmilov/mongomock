import pytest

import testing.services.compose_service as compose_service

from pymongo import MongoClient


class MongoService(compose_service.ComposeService):
    def __init__(self, config_file_path):
        super().__init__(config_file_path)

    def is_up(self):

        # TODO: parse yaml file for user and password.
        try:
            import socket
            socket.create_connection(('localhost', 27017))
            # client = MongoClient('mongodb://localhost:27017', username='ax_user', password='ax_pass')
            return True
        except:
            print('Mongo seems to be down.')
            return False


@pytest.fixture
def mongo_fixture(request):
    mongo = MongoService('../../devops/systemization/database/docker-compose.yml')

    mongo.start()

    def fin():
        mongo.stop()
        print('Stopped Mongo')

    request.addfinalizer(fin)
    return mongo
