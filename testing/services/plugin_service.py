import services.compose_parser
import services.compose_service
import requests
import axonius.ConfigReader
import json

API_KEY_HEADER = "x-api-key"


class PluginService(services.compose_service.ComposeService):
    def __init__(self, compose_file_path, config_file_path, vol_config_file_path):
        super().__init__(compose_file_path)
        self.parsed_compose_file = services.compose_parser.ServiceYmlParser(
            compose_file_path)
        port = self.parsed_compose_file.exposed_port
        self.endpoint = ('localhost', port)
        self.req_url = "http://{0}:{1}/api".format(
            self.endpoint[0], self.endpoint[1])
        self.config_file_path = config_file_path
        self.volatile_config_file_path = vol_config_file_path

    def version(self):
        return requests.get(self.req_url + "/version")

    def logger(self):
        raise NotImplemented("TBD!")

    def action_update(self, action_id):
        raise NotImplemented("TBD!")

    def schema(self, schema_type="general", api_key=None):
        if api_key is None:
            api_key = self.api_key

        return requests.get(self.req_url + "/schema/" + schema_type, headers={API_KEY_HEADER: api_key})

    def is_plugin_registered(self, core_service):
        unique_name = self.unique_name
        all_plugins = json.loads(core_service.register().content)

        return unique_name in all_plugins

    def is_up(self):
        return self._is_service_alive()

    def _is_service_alive(self):
        try:
            r = self.version()
            return r.status_code == 200
        except:
            return False

    @property
    def conf(self):
        return axonius.ConfigReader.PluginConfig(self.config_file_path)

    @property
    def vol_conf(self):
        return axonius.ConfigReader.PluginVolatileConfig(self.volatile_config_file_path)

    @property
    def api_key(self):
        return self.vol_conf.api_key

    @property
    def unique_name(self):
        return self.vol_conf.unique_name


class AdapterService(PluginService):
    def __init__(self, compose_file_path, config_file_path, vol_config_file_path):
        super().__init__(compose_file_path=compose_file_path, config_file_path=config_file_path,
                         vol_config_file_path=vol_config_file_path)

    def add_client(self, db, clients_details):
        db.add_client(self.unique_name, clients_details)
        return self.clients()  # post to clients forces a refresh!

    def devices(self):
        response = requests.get(self.req_url + "/devices",
                                headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200
        return dict(json.loads(response.content))

    def clients(self):
        return requests.post(self.req_url + "/clients", headers={API_KEY_HEADER: self.api_key})

    def action(self, action_type):
        raise NotImplemented("TBD!")
