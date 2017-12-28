import configparser
from axonius.consts import AdapterConsts
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


class PluginConfig(object):
    def __init__(self, config_file_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_file_path)

    @property
    def port(self):
        return self._config['DEBUG']['port']

    @property
    def host(self):
        return self._config['DEBUG']['host']

    @property
    def version(self):
        return self._config['DEFAULT']['version']

    @property
    def name(self):
        return self._config['DEFAULT']['name']

    @property
    def core_address(self):
        return self._config['DEBUG']['core_address']


class AdapterConfig(PluginConfig):
    def __init__(self, config_file_path):
        super().__init__(config_file_path)

    @property
    def default_sample_rate(self):
        return int(self._config['DEFAULT'][AdapterConsts.DEFAULT_SAMPLE_RATE])


class PluginVolatileConfig(object):
    def __init__(self, config_string):
        self._config = configparser.ConfigParser()
        self._config.read_string(config_string)

    @property
    def api_key(self):
        return self._config['registration']['api_key']

    @property
    def unique_name(self):
        return self._config['registration'][PLUGIN_UNIQUE_NAME]
