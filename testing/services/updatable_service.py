from typing import Callable

from pymongo.database import Database

from axonius.consts.plugin_consts import VERSION_COLLECTION


class UpdatablePluginMixin:
    """
    This must be a mixin that also inherits from PluginService
    """

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
            for x in [x for x in db.database_names() if x.startswith(self.plugin_name)]:
                to_call(db[x])
            self.db_schema_version = version
        except Exception as e:
            print(f'Could not upgrade {self.plugin_name} db to version {version}. Details: {e}')

    @property
    def __version_collection(self):
        return self.db.get_collection(self.plugin_name, VERSION_COLLECTION)
