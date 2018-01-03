import requests
import json

from axonius.config_reader import PluginConfig, PluginVolatileConfig, AdapterConfig
from axonius.plugin_base import VOLATILE_CONFIG_PATH
from services.compose_service import ComposeService

API_KEY_HEADER = "x-api-key"
UNIQUE_KEY_PARAM = "unique_name"


class PluginService(ComposeService):
    def __init__(self, service_dir, mode='', **kwargs):
        if mode == '':
            mode = 'override'
        compose_file_path = service_dir + '/docker-compose.yml'
        override_compose_file_path = service_dir + f'/docker-compose.{mode}.yml'
        super().__init__(compose_file_path, override_compose_file_path=override_compose_file_path, **kwargs)
        port = self.parsed_compose_file.exposed_port
        self.endpoint = ('localhost', port)
        self.req_url = "http://{0}:{1}/api".format(self.endpoint[0], self.endpoint[1])
        self.config_file_path = service_dir + '/src/plugin_config.ini'
        self.last_vol_conf = None

    def request(self, method, endpoint, api_key=None, headers=None, *vargs, **kwargs):
        if headers is None:
            headers = {}

        if api_key is not None:
            headers[API_KEY_HEADER] = api_key

        if 'data' in kwargs and isinstance(kwargs['data'], dict):
            kwargs['data'] = json.dumps(kwargs['data'])

        return getattr(requests, method)(url='{0}/{1}'.format(self.req_url, endpoint),
                                         headers=headers, *vargs, **kwargs)

    def get(self, endpoint, *vargs, **kwargs):
        return self.request('get', endpoint, *vargs, **kwargs)

    def put(self, endpoint, data, *vargs, **kwargs):
        return self.request('put', endpoint, data=data, *vargs, **kwargs)

    def post(self, endpoint, *vargs, **kwargs):
        return self.request('post', endpoint, *vargs, **kwargs)

    def delete(self, endpoint, *vargs, **kwargs):
        return self.request('delete', endpoint, *vargs, **kwargs)

    def version(self):
        return self.get('version', timeout=15)

    def get_supported_features(self):
        res = self.get('supported_features', timeout=15)
        assert res.status_code == 200
        return set(res.json())

    def trigger_check_registered(self):
        try:
            # Will trigger the plugin to check if he is registered. If not, the plugin will exit immediately
            self.get('trigger_registration_check', timeout=15)
        except:
            pass

    def logger(self):
        raise NotImplemented("TBD!")

    def action_update(self, action_id):
        raise NotImplemented("TBD!")

    def is_plugin_registered(self, core_service):
        unique_name = self.unique_name
        result = core_service.register(self.api_key, unique_name)
        return result.status_code == 200

    def is_up(self):
        return self._is_service_alive() and "Plugin" in self.get_supported_features()

    def _is_service_alive(self):
        try:
            self.trigger_check_registered()
            r = self.version()
            return r.status_code == 200
        except:
            return False

    @property
    def conf(self):
        return PluginConfig(self.config_file_path)

    @property
    def vol_conf(self):
        # Try to get the latest, but if the container is down, use the last data.
        (out, _, _) = self.get_file_contents_from_container(VOLATILE_CONFIG_PATH)
        self.last_vol_conf = PluginVolatileConfig(out.decode("utf-8"))

        return self.last_vol_conf

    @property
    def api_key(self):
        return self.vol_conf.api_key

    @property
    def unique_name(self):
        return self.vol_conf.unique_name


class AdapterService(PluginService):

    def add_client(self, client_details):
        self.clients(client_details)

    def devices(self):
        response = requests.get(self.req_url + "/devices",
                                headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, str(response)
        return dict(json.loads(response.content))

    def clients(self, client_data=None):
        if not client_data:
            response = requests.post(self.req_url + "/clients", headers={API_KEY_HEADER: self.api_key})
        else:
            response = requests.put(self.req_url + "/clients",
                                    headers={API_KEY_HEADER: self.api_key},
                                    json=client_data)
        assert response.status_code == 200, str(response)

    def action(self, action_type):
        raise NotImplemented("TBD!")

    def schema(self, schema_type="general", api_key=None):
        return self.get('{0}/{1}'.format('schema', schema_type), api_key=self.api_key if api_key is None else api_key)

    def is_up(self):
        return super().is_up() and "Adapter" in self.get_supported_features()

    @property
    def conf(self):
        return AdapterConfig(self.config_file_path)
