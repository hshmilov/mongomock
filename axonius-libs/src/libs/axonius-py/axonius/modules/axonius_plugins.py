"""
Get access to important utilities of core
"""
import re
from typing import List

from pymongo import MongoClient

from axonius.consts.plugin_consts import CORE_UNIQUE_NAME, GUI_PLUGIN_NAME, SYSTEM_SCHEDULER_PLUGIN_NAME, \
    AGGREGATOR_PLUGIN_NAME
from axonius.modules.plugin_settings import PluginSettings, ConfigurableConfigsGeneral


class AxoniusPlugins:
    def __init__(self, db: MongoClient):
        self.__db = db
        self.configurable_configs_general = ConfigurableConfigsGeneral(self.__db)

        # Easy reference for important -singular- plugins (singular means plugin_name == plugin_unique_name)
        self.core = AxoniusPlugin(db, CORE_UNIQUE_NAME)
        self.aggregator = AxoniusPlugin(db, AGGREGATOR_PLUGIN_NAME)
        self.gui = AxoniusPlugin(db, GUI_PLUGIN_NAME)
        self.system_scheduler = AxoniusPlugin(db, SYSTEM_SCHEDULER_PLUGIN_NAME)

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

        assert not re.search(r'_(\d+)$', plugin_unique_name)  # assert plugin unique name does not end with '_{number}'

        self.plugin_settings = PluginSettings(db, plugin_unique_name)
        self.configurable_configs = self.plugin_settings.configurable_configs
