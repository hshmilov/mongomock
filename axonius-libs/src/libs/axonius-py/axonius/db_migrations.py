import functools
import logging
import traceback
from typing import List

from axonius.utils.debug import redprint


def db_migration(raise_on_failure: bool, logger: logging.Logger = None):
    """
    Decorator for db migration functions
    :param logger: logger class
    :param raise_on_failure: if true, we will stop the whole migration process for this service on failure
    :return:
    """
    def wrap(func):
        try:
            index = func.__name__.split('_')[-1]
        except Exception:
            err = f'Wrong function name {func.__name__} for db migration'
            if logger:
                logger.exception(err)
            else:
                redprint(err)
            raise

        @functools.wraps(func)
        def actual_wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                err = f'Exception while upgrading {self.plugin_name} db to version {index}: {e}.'
                if logger:
                    logger.exception(err)
                else:
                    redprint(err)
                    traceback.print_exc()
                if raise_on_failure:
                    raise
        return actual_wrapper

    return wrap


class MigrationFailure(Exception):
    pass


class DBMigration:
    def __init__(self, migrations_prefix, migration_class, version_collection, version_fieldname):
        """
        :param migrations_prefix: migration functions prefix
        :param migration_class: class for running migrations
        :param version_collection: plugin version mongo collection
        :param version_fieldname: version name in mongo collection
        """
        self._migrations_prefix = migrations_prefix
        self._migration_class = migration_class
        self._version_collection = version_collection
        self._version_fieldname = version_fieldname

    @property
    def db_schema_version(self):
        version = self._version_collection.find_one({'name': self._version_fieldname})
        if version:
            return version.get('version', 0)
        return 0

    @db_schema_version.setter
    def db_schema_version(self, val):
        self._version_collection.update_one(
            {'name': self._version_fieldname},
            {
                '$set': {
                    'version': val
                }
            },
            upsert=True
        )

    @staticmethod
    def validate_migrations_list(migrations: List[str]):
        """
        Validate migrations order
        :param migrations: list of migrations functions name.
        :return:
        :raise: Exception on error
        """
        migrations_ids = [int(x.split('_')[-1]) for x in migrations]
        for i, migration_id in enumerate(migrations_ids):
            if i + 1 != migration_id:
                raise MigrationFailure(f'Error: Migration {i + 1} was skipped')

    def run_migrations(self, func_wrapper=None):
        """
        Sort and run all the migrations functions for the service
        :param func_wrapper: migration function wrapper
        :return:
        """
        migrations_list = [func for func in dir(self._migration_class)
                           if func.startswith(self._migrations_prefix)
                           and callable(getattr(self._migration_class, func))]

        if not migrations_list:
            return
        # sort migrations by version
        migrations_list.sort(key=lambda x: int(x.split('_')[-1]))
        self.validate_migrations_list(migrations_list)
        migrations_left = migrations_list[self.db_schema_version:]

        # run migrations
        for migration in migrations_left:
            migration_func = getattr(self._migration_class, migration)
            index = migrations_list.index(migration) + 1
            if func_wrapper:
                func_wrapper(index, migration_func)
            else:
                migration_func()
            self.db_schema_version = index
        if self.db_schema_version < len(migrations_list):
            raise MigrationFailure(f'Upgrade failed, db_schema_version is {self.db_schema_version}')
