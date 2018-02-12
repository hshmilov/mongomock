import os
import pymongo
import subprocess

from services.docker_service import DockerService
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from services.ports import DOCKER_PORTS


class MongoService(DockerService):
    def __init__(self):
        super().__init__('mongo', '../infrastructures/database')
        self.client = None
        exposed = self.exposed_ports[0]
        self.endpoint = ('localhost', exposed[0])
        self.connect()

    @property
    def exposed_ports(self):
        """
        :return: list of pairs (exposed_port, inner_port)
        """
        return [(DOCKER_PORTS[self.container_name], 27017)]

    @property
    def image(self):
        return 'mongo:3.6'

    @property
    def volumes(self):
        return [f'{self.container_name}_data:/data/db',
                '{0}:/docker-entrypoint-initdb.d'.format(os.path.join(self.service_dir, 'docker-entrypoint-initdb.d'))]

    @property
    def environment(self):
        return ['MONGO_INITDB_ROOT_USERNAME=ax_user',
                'MONGO_INITDB_ROOT_PASSWORD=ax_pass',
                'MONGO_INITDB_DATABASE=core']

    def get_dockerfile(self, mode=''):
        return None

    def build(self, mode='', runner=None):
        docker_pull = ['docker', 'pull', self.image]
        if runner is None:
            print(' '.join(docker_pull))
            subprocess.check_output(docker_pull, cwd=self.service_dir)
        else:
            runner.append_single(self.container_name, docker_pull, cwd=self.service_dir)

    def remove_image(self):
        pass  # We never want to remove this static image...

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

    def get_devices_db(self, aggregator_unique_name):
        return self.client[aggregator_unique_name]['devices_db']

    def get_devices(self, aggregator_unique_name):
        return self.get_devices_db(aggregator_unique_name).find({})
