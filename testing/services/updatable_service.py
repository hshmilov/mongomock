from typing import Callable

from pymongo.database import Database

from axonius.consts.plugin_consts import VERSION_COLLECTION
from axonius.db_migrations import DBMigration
from axonius.utils.debug import redprint


MIGRATION_PREFIX = '_update_schema'


class UpdatablePluginMixin:
    """
    This must be a mixin that also inherits from PluginService
    """

    def _upgrade_adapter_client_id(self, plugin_name: str, new_client_id_func: Callable, use_encryption=True):
        """
        Takes a plugin_name like 'symantec_adapter'. Then, for each plugin_unique_name of this adapter, and
        for each client in every plugin_unique_name, calls new_client_id_func with 'client_config'. Then sets the
        return value as the new client id.

        Do not specify 'use_encryption=False'. This is intended for older versions of Axonius where credentials were
        not encrypted.
        :return:
        """
        all_plugin_instances = list(self.db.client['core']['configs'].find({'plugin_name': plugin_name}))
        for plugin_instance in all_plugin_instances:
            if 'plugin_unique_name' not in plugin_instance:
                print(f'Error - No plugin unique name for document, bypassing: {plugin_instance}')
                continue
            plugin_unique_name = plugin_instance['plugin_unique_name']
            clients_db = self.db.client[plugin_unique_name]['clients']
            plugin_clients = list(clients_db.find({}))

            print(f'Upgrading {plugin_unique_name} with {len(plugin_clients)} clients..')
            for client in plugin_clients:
                if 'client_config' not in client:
                    print(f'Error - no client config for plugin, bypassing: {client}')
                    continue

                client_config = client['client_config'].copy()
                if use_encryption:
                    self.decrypt_dict(client_config)

                new_client_id = new_client_id_func(client_config)
                clients_db.update(
                    {
                        'client_id': client['client_id']
                    },
                    {
                        '$set':
                            {
                                'client_id': new_client_id
                            }
                    }
                )

    @property
    def db_schema_version(self):
        res = self.__version_collection.find_one({'name': 'schema'})
        if not res:
            return 0
        return res.get('version', 0)

    @db_schema_version.setter
    def db_schema_version(self, val):
        self.__version_collection.replace_one({'name': 'schema'},
                                              {'name': 'schema', 'version': val},
                                              upsert=True)

    def _update_nonsingleton_to_schema(self, version: int, to_call: Callable[[Database], None]):
        """
        If your plugin isn't a singleton plugin (like, GUI), i.e. it doesn't pass 'requested_unique_plugin_name'
        in __init__ to PluginBase, it means that there could be multiple instances of it with different
        plugin_unique_names.
        In this case, when you run an upgrade script, you'd want to update all the DBs.
        :param version: The version to set to
        :param to_call: The upgrading function to the given version
        """
        print(f'upgrade to schema {version}')
        try:
            db = self.db.client
            for x in [x for x in db.database_names() if x != self.plugin_name and x.startswith(self.plugin_name)]:
                to_call(db[x])
            self.db_schema_version = version
        except Exception as e:
            redprint(f'Could not upgrade {self.plugin_name} db to version {version}. Details: {e}')

    @property
    def __version_collection(self):
        return self.db.get_collection(self.plugin_name, VERSION_COLLECTION)

    def _run_all_migrations(self, nonsingleton: bool = False):
        migrator = DBMigration(migrations_prefix=MIGRATION_PREFIX,
                               migration_class=self,
                               version_collection=self.__version_collection,
                               version_fieldname='schema')
        func_wrapper = self._upgrade_adapter_client_id if nonsingleton else None
        migrator.run_migrations(func_wrapper)
