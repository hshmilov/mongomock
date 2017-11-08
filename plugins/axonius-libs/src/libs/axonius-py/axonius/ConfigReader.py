import configparser


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
    def unique_name(self):
        return self._config['registration']['plugin_unique_name']

    @property
    def version(self):
        return self._config['DEFAULT']['version']

    @property
    def name(self):
        return self._config['DEFAULT']['name']

    @property
    def core_address(self):
        return self._config['DEBUG']['core_address']

    @property
    def api_key(self):
        return self._config['registration']['api_key']
