import time
from collections import defaultdict
from typing import Optional

import psutil
import pymongo
from retrying import retry

from axonius.plugin_base import EntityType
from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.plugin_consts import (PLUGIN_UNIQUE_NAME, AGGREGATOR_PLUGIN_NAME, GUI_PLUGIN_NAME,
                                          CONFIGURABLE_CONFIGS_COLLECTION, CORE_UNIQUE_NAME, REPORTS_PLUGIN_NAME)
from axonius.consts.gui_consts import (GETTING_STARTED_CHECKLIST_SETTING)
from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService

# Ideally, the replicaSet would be specified here (the same way it does in plugin_base.py)
# However this code is ran within the context of the machine and not a specific docker, so
# accessing the DB is done by accessing 'localhost', with a forwarded port.
#
# If the replicaSet is specified here, then the machine will try to access the
# endpoints specified in that replicaSet, which are only accessible from within the
# docker network, and thus, inaccessible to the context this code is running from.
connection_line = 'mongodb://{user}:{password}@{addr}:{port}'.format(user='ax_user',
                                                                     password='ax_pass',
                                                                     addr='localhost',
                                                                     port=27017)


class MongoService(WeaveService):
    # The reason we're using just one client is that you must'nt have many instance of the client
    # because mongo is buggy as hell and opens 600 threads and crashes your app
    client = pymongo.MongoClient(connection_line)

    def __init__(self):
        super().__init__('mongo', '../infrastructures/database')

    @property
    def exposed_ports(self):
        """
        :return: list of pairs (exposed_port, inner_port)
        """
        return [(DOCKER_PORTS[self.container_name], 27017)]

    @property
    def max_allowed_memory(self):
        total_memory = psutil.virtual_memory().total / (1024 ** 2)  # total memory, in mb
        total_memory = int(total_memory * 0.75)  # We want mongodb to always catch 75% of ram.
        return total_memory

    @property
    def memory_swappiness(self) -> Optional[int]:
        """
        A swappiness setting of zero means that the disk will be avoided unless
        absolutely necessary (you run out of memory), while a swappiness setting of 100 means that programs will be
        swapped to disk almost instantly.
        :return:
        """
        # mongo recommends to not set this to 0
        # https://docs.mongodb.com/manual/administration/production-notes/
        return None

    @property
    def image(self):
        return 'mongo:4.2'

    @retry(stop_max_attempt_number=3, wait_fixed=5)
    def configure_replica_set(self):
        self.run_command_in_container('mongo /docker-entrypoint-initdb.d/configure_replica_set.js')

    def deprecate_a_leftover_db(self, plugin_unique_name: str):
        admin_db = self.client['admin']
        for collection_name in self.client[plugin_unique_name].list_collection_names():
            admin_db.command({
                'renameCollection': f'{plugin_unique_name}.{collection_name}',
                'to': f'DEPRECATED_{plugin_unique_name}.{collection_name}'
            })

        doc = self.client['core']['configs'].find_one_and_delete({
            'plugin_unique_name': plugin_unique_name
        })
        if doc:
            self.client['core']['configs_deprecated'].insert_one(doc)

    def clean_old_databases(self):
        registered_plugins = list(self.client['core']['configs'].find({}))

        # finding duplicates in the core configs

        by_plugin_name = defaultdict(list)
        for x in registered_plugins:
            by_plugin_name[x['plugin_name']].append(x)

        # Plugins that we're updating to become a singleton
        plugins_in_question = ['reports', 'general_info', 'execution',
                               'static_correlator', 'static_users_correlator', 'device_control']

        for x in plugins_in_question:
            instances = by_plugin_name[x]
            if len(instances) > 1:
                unique_names = {plugin['plugin_unique_name'] for plugin in instances}
                print(f'Found duplications ({len(unique_names)}): {x}: ' + ', '.join(unique_names))

                last_seen = max(instances, key=lambda x: x['last_seen'])
                leftover_dbs = [
                    x['plugin_unique_name']
                    for x
                    in instances
                    if x['plugin_unique_name'] != last_seen['plugin_unique_name']
                ]

                print(f'{last_seen["plugin_unique_name"]} is the newest, olds are all others: ' +
                      ', '.join(leftover_dbs))

                for leftover in leftover_dbs:
                    print(f'Deprecating {leftover}')
                    self.deprecate_a_leftover_db(leftover)

    def start(self, mode='',
              allow_restart=False,
              rebuild=False,
              *args, **kwargs):
        super().start(mode, allow_restart, rebuild, *args, **kwargs)

        self.wait_for_service()
        print("Mongo master is online")

        self.configure_replica_set()
        # The sleep here is only relevant to the core, because it runs first.
        # The intention of this sleep is to allow the DB to initialize itself properly and then
        # accessing it without specifying a replicaSet will work.
        # This might be solved by using a more sophisticated docker setup, but it will do for now.
        time.sleep(10)

        self.clean_old_databases()

        print("Finished setting up mongo")

    def wait_for_service(self, timeout=60 * 45):
        # We wait much longer for mongo, because in some customers, a hard restart can cause a corruption in the db
        # which needs a restore. Depending on the size of the environment and the speed of the hard disk, this can
        # be very fast or very slow.
        #
        # On the other hand if we don't wait enough, a restart will be made (to identify weave bugs) which will lead
        # to the db being corrupt again. we are trying to avoid that.
        super().wait_for_service(timeout)

    @property
    def _additional_parameters(self):
        return ['mongod',
                '--keyFile', '/docker-entrypoint-initdb.d/mongodb.key',
                '--replSet', 'axon-cluster',
                '--config', '/etc/mongod.conf',
                ]

    def get_dockerfile(self, *args, **kwargs):
        return f"""
    FROM mongo:4.2
    
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
            self.client.server_info()
        except Exception as err:
            print(err)
            return False
        return True

    def is_up(self, *args, **kwargs):
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
        return self.client[GUI_PLUGIN_NAME]['users']

    def gui_config_collection(self):
        return self.client[GUI_PLUGIN_NAME][CONFIGURABLE_CONFIGS_COLLECTION]

    def remove_gui_dynamic_fields(self, entity_type: EntityType):
        fields_collection_name = 'users_fields' if (entity_type == EntityType.Users) else 'devices_fields'
        fields_collection = self.client[AGGREGATOR_PLUGIN_NAME][fields_collection_name]

        fields_collection.update_one({
            'name': 'dynamic',
            'plugin_unique_name': GUI_PLUGIN_NAME
        }, {
            '$set': {
                'schema.items': []
            }
        })
        fields_collection.update_one({
            'name': 'exist',
            'plugin_unique_name': GUI_PLUGIN_NAME
        }, {
            '$set': {
                'fields': []
            }
        })

    def restore_gui_entity_views(self, entity_type: EntityType):
        views_collection_name = 'user_views' if (entity_type == EntityType.Users) else 'device_views'
        self.client[GUI_PLUGIN_NAME][views_collection_name].update_many({
            'archived': True
        }, {
            '$set': {
                'archived': False
            }
        })
        self.client[GUI_PLUGIN_NAME][views_collection_name].delete_many({
            'predefined': {
                '$exists': False
            }
        })

    def gui_reports_config_collection(self):
        return self.client[GUI_PLUGIN_NAME]['reports_config']

    def gui_dashboard_spaces_collection(self):
        return self.client[GUI_PLUGIN_NAME]['dashboard_spaces']

    def gui_dashboard_collection(self):
        return self.client[GUI_PLUGIN_NAME]['dashboard']

    def gui_getting_started_auto(self):
        getting_started_doc = self.client[GUI_PLUGIN_NAME]['getting_started'].find_one({})
        if getting_started_doc is None:
            return False
        return getting_started_doc.get('settings', {}).get('autoOpen', False)

    def core_configurable_config_collection(self):
        return self.client[CORE_UNIQUE_NAME][CONFIGURABLE_CONFIGS_COLLECTION]

    def core_settings_getting_started(self):
        config = self.core_configurable_config_collection().find_one(
            {'config_name': CORE_CONFIG_NAME}).get('config', {})
        return config.get(GETTING_STARTED_CHECKLIST_SETTING, {}).get('enabled', False)

    def enforcements_collection(self):
        return self.client[REPORTS_PLUGIN_NAME][REPORTS_PLUGIN_NAME]
