import logging

from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS

logger = logging.getLogger(f"axonius.{__name__}")
from typing import Tuple, Dict, Iterable


def does_method_belongs_to_class(method, cls) -> bool:
    """
    The condition checks that the method was explicitly implemented in the given class
    """
    return method.__qualname__.startswith(f"{cls.__name__}.")


class Configurable(object):
    """
    Inheriting this allows a class that is a part of a plugin/adapter to interact with the GUI
    requesting a config from the user - a config that can be modified on the fly.
    This must be a subclass of plugin_base
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def _db_config_schema(cls) -> dict:
        """
        Return the schema this class wants to have for the config
        """
        pass

    @classmethod
    def _db_config_default(cls):
        """
        Return the default configuration for this class
        """
        pass

    def _on_config_update(self, config):
        """
        Virtual
        This is called on every inheritor when the config was updated.
        """
        pass

    @classmethod
    def __recurse_tree(cls, recurse_type) -> Iterable:
        """
        Returns all classes in the inheritance tree that also inherit from Configurable
        """
        if Configurable in recurse_type.__bases__:
            yield recurse_type
        for base in recurse_type.__bases__:
            if base is object or base is Configurable:
                continue
            yield from cls.__recurse_tree(base)

    @classmethod
    def __get_all_configs_and_defaults(cls) -> Iterable[Tuple[object, Dict, Dict]]:
        """
        Get all config names, schemas and examples
        """
        for inheritor in cls.__recurse_tree(cls):
            if does_method_belongs_to_class(inheritor._db_config_schema, inheritor):
                yield inheritor, inheritor._db_config_schema.__func__(cls), inheritor._db_config_default.__func__(cls)

    def renew_config_from_db(self):
        """
        Fetch all configs from the DB and update the classes
        """
        configs = self._get_collection(CONFIGURABLE_CONFIGS)

        for inheritor in type(self).__recurse_tree(type(self)):
            if not does_method_belongs_to_class(inheritor._db_config_schema, inheritor):
                # Classes without a db_scheme aren't expecting a config
                continue

            from_db = configs.find_one({
                'config_name': inheritor.__name__
            })
            if from_db is None:
                logger.critical("Configs are corrupted")
                logger.error(f"Can't find log for {inheritor.__name__}! Inserting default!")
                configs.update_one(filter={
                    'config_name': inheritor.__name__
                },
                    update={
                        "$setOnInsert": {
                            'config_name': inheritor.__name__,
                            'config': inheritor._db_config_default()
                        }
                },
                    upsert=True)
                config_to_save = inheritor._db_config_default()
            else:
                config_to_save = from_db['config']

            # Call _on_config_update on the class if it was implemented
            if does_method_belongs_to_class(inheritor._on_config_update, inheritor):
                inheritor._on_config_update(self, config_to_save)

    def _update_schema(self):
        """
        Updates DB with the schema and default configs (if no other config exists)
        """
        schemas = self._get_collection("config_schemas")
        configs = self._get_collection(CONFIGURABLE_CONFIGS)
        for config_class, config_schema, config_default in self.__get_all_configs_and_defaults():
            old_schema = schemas.find_one_and_replace(filter={
                'config_name': config_class.__name__,
            }, replacement={
                'config_name': config_class.__name__,
                'schema': config_schema
            }, upsert=True) or {}

            config_to_insert = {
                'config_name': config_class.__name__,
                'config': config_default
            }
            if old_schema.get('schema') == config_schema:
                # if the schema didn't change it means we don't override the current config with the
                # default config.

                # insert if nonexistent
                configs.update_one(filter={
                    'config_name': config_class.__name__
                },
                    update={
                        "$setOnInsert": config_to_insert
                },
                    upsert=True)
            else:
                # if the schema did change it is likely that the old config isn't compatible so we must overthrow
                # it with the default config
                configs.replace_one(filter={
                    'config_name': config_class.__name__
                },
                    replacement=config_to_insert,
                    upsert=True)
