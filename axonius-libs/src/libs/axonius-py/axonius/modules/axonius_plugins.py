"""
Get access to important utilities of core
"""
from typing import List, Optional

from pymongo import MongoClient

from axonius.consts.plugin_consts import CORE_UNIQUE_NAME, GUI_PLUGIN_NAME, SYSTEM_SCHEDULER_PLUGIN_NAME, \
    AGGREGATOR_PLUGIN_NAME
from axonius.db.db_client import get_db_client
from axonius.modules.plugin_settings import PluginSettings, ConfigurableConfigsGeneral


class AxoniusPlugins:
    def __init__(self, db: Optional[MongoClient] = None):
        self.__db = db if db else get_db_client()
        self.configurable_configs_general = ConfigurableConfigsGeneral(self.__db)

        # Easy reference for important -singular- plugins (singular means plugin_name == plugin_unique_name)
        self.core = AxoniusPlugin(self.__db, CORE_UNIQUE_NAME)
        self.aggregator = AxoniusPlugin(self.__db, AGGREGATOR_PLUGIN_NAME)
        self.gui = AxoniusPlugin(self.__db, GUI_PLUGIN_NAME)
        self.system_scheduler = AxoniusPlugin(self.__db, SYSTEM_SCHEDULER_PLUGIN_NAME)

    def get_plugin_names_with_config(self, config_name: str, config: dict) -> List[str]:
        """
        Get plugin names that contain specific config. e.g.

        get_plugin_names_with_config('DiscoverySchema', {'enabled': True, 'o': True}) == ['aws_adapter', 'esx_adapter']
        """
        return self.configurable_configs_general.get_plugin_names_with_config(config_name, config)

    def get_plugin_settings(self, plugin_name: str):
        return PluginSettings(self.__db, plugin_name)


class AxoniusPlugin:
    def __init__(self, db: MongoClient, plugin_unique_name):
        self.__plugin_unique_name = plugin_unique_name
        self.__db = db

        self.plugin_settings = PluginSettings(db, plugin_unique_name)
        self.configurable_configs = self.plugin_settings.configurable_configs
        self.config_schemas = self.plugin_settings.config_schemas
