import pytest
import pymongo

import services.compose_service
from services.simple_fixture import initalize_fixture


class MongoService(services.compose_service.ComposeService):
    def __init__(self, endpoint=('localhost', 27018),
                 compose_file_path='../devops/systemization/database/docker-compose.yml'):
        super().__init__(compose_file_path)
        self.endpoint = endpoint
        self.client = None

    def is_mongo_alive(self):
        try:
            connection_line = "mongodb://{user}:{password}@{addr}:{port}".format(user="ax_user",
                                                                                 password="ax_pass",
                                                                                 addr=self.endpoint[0],
                                                                                 port=self.endpoint[1])
            self.client = pymongo.MongoClient(connection_line)
            self.client.server_info()
            print("Mongo connection worked")
            return True
        except Exception as err:
            print(err)
            return False

    def is_up(self):
        return self.is_mongo_alive()

    def get_configs(self):
        return list(iter(self.client['core']['configs'].find()))

    def get_unique_plugin_config(self, unique_plugin_name):
        configs = self.get_configs()
        plugin_config = list(
            filter(lambda k: k['plugin_unique_name'] == unique_plugin_name, configs))
        assert 1 == len(plugin_config)
        return plugin_config[0]

    def add_client(self, adapter_name, client_details):
        self.client[adapter_name].clients.insert_one(client_details)


@pytest.fixture(scope="session")
def mongo_fixture(request):
    service = MongoService()
    initalize_fixture(request, service)
    return service
