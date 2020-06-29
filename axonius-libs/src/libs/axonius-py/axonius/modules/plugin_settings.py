"""
Different settings for plugins in the system
"""
import re
from typing import Optional

from pymongo import MongoClient

from axonius.consts.plugin_consts import CORE_UNIQUE_NAME, PLUGIN_NAME, DISCOVERY_CONFIG_NAME


class Consts:
    AllConfigurableConfigs = 'all_configurable_configs'
    AllConfigurableConfigsSchemas = 'all_configurable_configs_schemas'
    AllAdapterClientConfigsSchemas = 'all_adapter_client_schemas'
    ConfigName = 'config_name'
    Config = 'config'
    Schema = 'schema'
    AllPluginSettingsKeyVal = 'all_plugin_settings_keyval'


class PluginSettingsNamespace:
    def __init__(self, db: MongoClient):
        self.__db = db

    def get_plugin(self, plugin_name: str):
        return PluginSettings(self.__db, plugin_name)


class PluginSettings:
    def __init__(self, db: MongoClient, plugin_name: str):
        # If you fail on the following line, this means you passed plugin_unique_name to here. But this only supports
        # plguin name and not plugin unique name!
        assert not re.search(r'_(\d+)$', plugin_name)

        self.__db = db
        self.__plugin_name = plugin_name
        self.configurable_configs = ConfigurableConfigs(self.__db, self.__plugin_name)
        self.config_schemas = ConfigurableConfigsSchemas(self.__db, self.__plugin_name)
        self.plugin_settings_keyval = PluginSettingsKeyVal(self.__db, self.__plugin_name)

    @property
    def adapter_client_schema(self):
        schema = self.__db[CORE_UNIQUE_NAME][Consts.AllAdapterClientConfigsSchemas].find_one(
            {
                PLUGIN_NAME: self.__plugin_name
            }
        )

        if schema:
            return schema.get(Consts.Schema)

        return None

    @adapter_client_schema.setter
    def adapter_client_schema(self, schema: dict):
        self.__db[CORE_UNIQUE_NAME][Consts.AllAdapterClientConfigsSchemas].replace_one(
            {
                PLUGIN_NAME: self.__plugin_name,
            },
            {
                PLUGIN_NAME: self.__plugin_name,
                Consts.Schema: schema
            },
            upsert=True
        )


class PluginSettingsKeyVal:
    def __init__(self, db: MongoClient, plugin_name: str):
        self.__db = db
        self.__plugin_name = plugin_name

    def __get(self, key):
        res = self.__db[CORE_UNIQUE_NAME][Consts.AllPluginSettingsKeyVal].find_one(
            {
                PLUGIN_NAME: self.__plugin_name,
                f'data.{key}': {'$exists': True}
            }
        ) or {}

        return res.get('data', {}).get(key)

    def __set(self, key, value):
        self.__db[CORE_UNIQUE_NAME][Consts.AllPluginSettingsKeyVal].update_one(
            {
                PLUGIN_NAME: self.__plugin_name,
                f'data.{key}': {'$exists': True}
            },
            {
                '$set': {
                    f'data.{key}': value
                }
            },
            upsert=True
        )

    def __delete(self, key):
        self.__db[CORE_UNIQUE_NAME][Consts.AllPluginSettingsKeyVal].update_one(
            {
                PLUGIN_NAME: self.__plugin_name,
                f'data.{key}': {'$exists': True}
            },
            {
                '$unset': {
                    f'data.{key}': 1
                }
            }
        )

    def __getitem__(self, key):
        return self.__get(key)

    def __setitem__(self, key, value):
        return self.__set(key, value)

    def __delitem__(self, key):
        return self.__delete(key)


class ConfigurableConfigsGeneral:
    def __init__(self, db: MongoClient):
        self.__db = db

    def get_plugin_names_with_config(self, config_name: str, config: dict):
        res = self.__db[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].find(
            {
                Consts.ConfigName: config_name,
                **{f'{Consts.Config}.{key}': value for key, value in config.items()}
            },
            projection={PLUGIN_NAME: 1}
        )

        return sorted([x[PLUGIN_NAME] for x in res])


class ConfigurableConfigs:
    def __init__(self, db: MongoClient, plugin_name: str):
        self.__db = db
        self.__plugin_name = plugin_name
        self.__adapter_class_name = ''.join([x.capitalize() for x in plugin_name.split('_')])

    def __get(self, config_name: str) -> Optional[dict]:
        config = self.__db[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].find_one(
            {
                PLUGIN_NAME: self.__plugin_name,
                Consts.ConfigName: config_name
            }
        )

        if config:
            return config.get(Consts.Config)

        return None

    def __set(self, config_name: str, config: dict):
        self.__db[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].replace_one(
            {
                PLUGIN_NAME: self.__plugin_name,
                Consts.ConfigName: config_name
            },
            {
                PLUGIN_NAME: self.__plugin_name,
                Consts.ConfigName: config_name,
                Consts.Config: config
            },
            upsert=True
        )

    def delete_config(self, config_name: str):
        self.__db[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].delete_one(
            {
                PLUGIN_NAME: self.__plugin_name,
                Consts.ConfigName: config_name
            }
        )

    def update_config(self, config_name: str, config: dict, upsert: bool = False):
        """
        Updates a configuration instead of replacing it.
        :param config_name:
        :param config:
        :param upsert:
        :return:
        """
        self.__db[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].update_one(
            {
                PLUGIN_NAME: self.__plugin_name,
                Consts.ConfigName: config_name
            },
            {
                '$set': {
                    **{f'{Consts.Config}.{key}': value for key, value in config.items()}
                }
            },
            upsert=upsert
        )

    def get_all(self) -> dict:
        return {
            x[Consts.ConfigName]: x.get(Consts.Config) or {}
            for x in self.__db[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].find({PLUGIN_NAME: self.__plugin_name})
        }

    @property
    def adapter_configuration(self) -> dict:
        return self['AdapterBase']

    @adapter_configuration.setter
    def adapter_configuration(self, val: dict):
        self['AdapterBase'] = val

    @property
    def discovery_configuration(self) -> dict:
        return self[DISCOVERY_CONFIG_NAME]

    @discovery_configuration.setter
    def discovery_configuration(self, val: dict):
        self[DISCOVERY_CONFIG_NAME] = val

    @property
    def unique_configuration(self) -> dict:
        return self[self.__adapter_class_name]

    @unique_configuration.setter
    def unique_configuration(self, val: dict):
        self[self.__adapter_class_name] = val

    def __getitem__(self, index):
        return self.__get(str(index))

    def __setitem__(self, key, value: dict):
        assert isinstance(value, dict), f'Configurable Config must be a dict. Got {str(value)}'
        self.__set(str(key), value)


class ConfigurableConfigsSchemas:
    def __init__(self, db: MongoClient, plugin_name: str):
        self.__db = db
        self.__plugin_name = plugin_name

    def __get(self, config_name: str) -> Optional[dict]:
        schema = self.__db[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigsSchemas].find_one(
            {
                PLUGIN_NAME: self.__plugin_name,
                Consts.ConfigName: config_name
            }
        )

        if schema:
            return schema.get(Consts.Schema)

        return None

    def __set(self, config_name: str, schema: dict):
        self.__db[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigsSchemas].replace_one(
            {
                PLUGIN_NAME: self.__plugin_name,
                Consts.ConfigName: config_name
            },
            {
                PLUGIN_NAME: self.__plugin_name,
                Consts.ConfigName: config_name,
                Consts.Schema: schema
            },
            upsert=True
        )

    def get_all(self) -> dict:
        return {
            x[Consts.ConfigName]: x.get(Consts.Schema) or {}
            for x in self.__db[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigsSchemas].find(
                {PLUGIN_NAME: self.__plugin_name}
            )
        }

    def __getitem__(self, index):
        return self.__get(str(index))

    def __setitem__(self, key, value: dict):
        assert isinstance(value, dict), f'Config Schema must be a dict. Got {str(value)}'
        self.__set(str(key), value)
