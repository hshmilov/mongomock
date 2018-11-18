import logging
from typing import Dict, Iterable, Tuple

from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS_COLLECTION

logger = logging.getLogger(f'axonius.{__name__}')


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
        configs = self._get_collection(CONFIGURABLE_CONFIGS_COLLECTION)

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

    @staticmethod
    def __try_automigrate_config_schema(new_schema, old_data, default_data) -> dict:
        """
        Once in a while a developer approaches a Configurable plugin and wishes to change the schema and defaults!
        We don't want to lose the old configuration so we really want to try to keep as much of it as possible
        This adds missing fields from the default configuration. It will not delete existing fields.
        This supports changing a field to an array and vice versa.
        :param new_schema: the new schema from the plugin
        :param old_data: the data (values) currently in the database
        :param default_data: the default data from the plugin
        :return: the data, which conforms to the new_schema, while preserving the most from the old_schema
        """
        schema_type = new_schema['type']

        if schema_type == 'file':  # file is a special case, it's sometimes a dict and sometimes not
            if old_data is not None:
                return old_data
            return default_data

        if schema_type != 'array':  # assuming scalar

            if isinstance(old_data, dict):
                # if a field has changed from array to scalar we want to discard the array
                return default_data

            return old_data

        assert schema_type == 'array'

        if not isinstance(old_data, dict):
            # in the case where a field changed to a property "old_data" will not be a dict
            old_data = {}

        returned_dict = {}
        items = new_schema['items']
        if isinstance(items, list):
            for item in items:
                name = item['name']
                if name not in old_data:
                    returned_dict[name] = default_data[name]
                else:
                    returned_dict[name] = Configurable.__try_automigrate_config_schema(item,
                                                                                       old_data.get(name),
                                                                                       default_data.get(name))
        elif isinstance(items, dict):
            if old_data is not None:
                returned_dict = old_data
            else:
                returned_dict = default_data

        return returned_dict

    def _update_schema(self):
        """
        Updates DB with the schema and default configs (if no other config exists)
        """
        schemas = self._get_collection("config_schemas")
        configs = self._get_collection(CONFIGURABLE_CONFIGS_COLLECTION)
        for config_class, config_schema, config_default in self.__get_all_configs_and_defaults():
            old_schema = schemas.find_one_and_replace(filter={
                'config_name': config_class.__name__,
            }, replacement={
                'config_name': config_class.__name__,
                'schema': config_schema
            }, upsert=True) or {}
            old_schema = old_schema.get('schema')

            if old_schema == config_schema:
                # if the schema didn't change it means we don't override the current config with the
                # default config.

                # insert if nonexistent
                configs.update_one(filter={
                    'config_name': config_class.__name__
                },
                    update={
                        "$setOnInsert": {
                            'config_name': config_class.__name__,
                            'config': config_default
                        }
                },
                    upsert=True)
            else:
                # if the schema did change it is likely that the old config isn't compatible so we must fix
                # it according to schema
                previous_config = configs.find_one(filter={
                    'config_name': config_class.__name__
                }) or {}
                previous_config = previous_config.get('config')
                logger.info(f"Got previous - {previous_config}, default = {config_default}")
                if previous_config:
                    previous_config = self.__try_automigrate_config_schema(config_schema,
                                                                           previous_config,
                                                                           config_default)
                else:
                    previous_config = config_default
                configs.replace_one(filter={
                    'config_name': config_class.__name__
                },
                    replacement={
                        'config_name': config_class.__name__,
                        'config': previous_config
                },
                    upsert=True)
