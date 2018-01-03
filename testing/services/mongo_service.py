import pytest
import pymongo

from services.compose_service import ComposeService
from services.simple_fixture import initialize_fixture
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


class MongoService(ComposeService):
    def __init__(self, endpoint=('localhost', 27018), **kwargs):
        super().__init__('../infrastructures/database/docker-compose.yml', **kwargs)
        self.client = None
        self.endpoint = endpoint
        self.connect()

    def is_mongo_alive(self):
        try:
            self.connect()
            self.client.server_info()
        except Exception as err:
            print(err)
            return False
        print("Mongo connection worked")
        return True

    def connect(self):
        connection_line = "mongodb://{user}:{password}@{addr}:{port}".format(user="ax_user",
                                                                             password="ax_pass",
                                                                             addr=self.endpoint[0],
                                                                             port=self.endpoint[1])
        self.client = pymongo.MongoClient(connection_line)

    def is_up(self):
        return self.is_mongo_alive()

    def get_configs(self):
        return list(iter(self.client['core']['configs'].find()))

    def get_unique_plugin_config(self, unique_plugin_name):
        configs = self.get_configs()
        plugin_config = list(filter(lambda k: k[PLUGIN_UNIQUE_NAME] == unique_plugin_name, configs))
        assert len(plugin_config) == 1
        return plugin_config[0]

    def get_collection(self, db_name, collection_name):
        """
        Returns a specific collection.

        :param str collection_name: The name of the collection we want to get.
        :param str db_name: The name of the db.

        :return: list(dict)
        """
        return self.client[db_name][collection_name]

    def get_databases(self):
        return self.client.database_names()

    def get_devices(self, aggregator_unique_name):
        return self.client[aggregator_unique_name]['devices_db'].find({})


@pytest.fixture(scope="module")
def mongo_fixture(request):
    service = MongoService()
    initialize_fixture(request, service)
    return service
