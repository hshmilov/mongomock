import os
import time

import psutil
import pymongo

from axonius.plugin_base import EntityType
from axonius.consts.plugin_consts import (PLUGIN_UNIQUE_NAME, AGGREGATOR_PLUGIN_NAME, GUI_NAME,
                                          CONFIGURABLE_CONFIGS_COLLECTION)
from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService


class MongoService(WeaveService):
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
    def max_allowed_memory(self):
        total_memory = psutil.virtual_memory().total / (1024 ** 2)  # total memory, in mb
        total_memory = int(total_memory * 0.50)  # We want mongodb to always catch 50% of ram.
        return total_memory

    @property
    def image(self):
        return 'mongo:4.0'

    def start(self, mode='',
              allow_restart=False,
              rebuild=False,
              *args, **kwargs):
        super().start(mode, allow_restart, rebuild, *args, **kwargs)

        self.wait_for_service()
        print("Mongo master is online")

        self.run_command_in_container("mongo /docker-entrypoint-initdb.d/configure_replica_set.js")
        # The sleep here is only relevant to the core, because it runs first.
        # The intention of this sleep is to allow the DB to initialize itself properly and then
        # accessing it without specifying a replicaSet will work.
        # This might be solved by using a more sophisticated docker setup, but it will do for now.
        time.sleep(10)
        print("Finished setting up mongo")

    @property
    def _additional_parameters(self):
        cache_size = int(0.5 * (self.max_allowed_memory - 1024) / 1024)
        return ['mongod',
                '--keyFile', '/docker-entrypoint-initdb.d/mongodb.key',
                '--replSet', 'axon-cluster',
                '--config', '/etc/mongod.conf',
                f'--wiredTigerCacheSizeGB={cache_size}'
                ]

    def get_dockerfile(self, *args, **kwargs):
        return f"""
    FROM mongo:4.0
    
    COPY docker-entrypoint-initdb.d/* /docker-entrypoint-initdb.d/
    COPY mongod.conf /etc/mongod.conf
    RUN chmod 600 /docker-entrypoint-initdb.d/*
    RUN chown mongodb:mongodb /docker-entrypoint-initdb.d/*
    """[1:]

    def get_main_file(self):
        return ''

    @property
    def volumes(self):
        return [f'{self.container_name}_data:/data/db']

    @property
    def environment(self):
        return ['MONGO_INITDB_ROOT_USERNAME=ax_user',
                'MONGO_INITDB_ROOT_PASSWORD=ax_pass',
                'MONGO_INITDB_DATABASE=core']

    def remove_image(self):
        pass  # We never want to remove this static image...

    def is_mongo_alive(self):
        try:
            self.connect()
            self.client.server_info()
        except Exception as err:
            print(err)
            return False
        return True

    def connect(self):
        # Ideally, the replicaSet would be specified here (the same way it does in plugin_base.py)
        # However this code is ran within the context of the machine and not a specific docker, so
        # accessing the DB is done by accessing 'localhost', with a forwarded port.
        #
        # If the replicaSet is specified here, then the machine will try to access the
        # endpoints specified in that replicaSet, which are only accessible from within the
        # docker network, and thus, inaccessible to the context this code is running from.

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
        return self.client.list_database_names()

    def get_entity_db(self, entity_type: EntityType):
        if entity_type == EntityType.Users:
            return self.client[AGGREGATOR_PLUGIN_NAME]['users_db']
        if entity_type == EntityType.Devices:
            return self.client[AGGREGATOR_PLUGIN_NAME]['devices_db']

    def get_historical_entity_db_view(self, entity_type: EntityType):
        if entity_type == EntityType.Users:
            return self.client[AGGREGATOR_PLUGIN_NAME]['historical_users_db_view']
        if entity_type == EntityType.Devices:
            return self.client[AGGREGATOR_PLUGIN_NAME]['historical_devices_db_view']

    def gui_users_collection(self):
        return self.client[GUI_NAME]['users']

    def gui_config_collection(self):
        return self.client[GUI_NAME][CONFIGURABLE_CONFIGS_COLLECTION]

    def get_gui_entity_fields(self, entity_type: EntityType):
        if entity_type == EntityType.Users:
            return self.client[GUI_NAME]['users_fields']
        if entity_type == EntityType.Devices:
            return self.client[GUI_NAME]['devices_fields']
