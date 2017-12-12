import services.compose_parser
import services.compose_service
import requests
import axonius.ConfigReader
import json
import tempfile
import time

API_KEY_HEADER = "x-api-key"
UNIQUE_KEY_PARAM = "unique_name"

from axonius.PluginBase import VOLATILE_CONFIG_PATH


class PluginService(services.compose_service.ComposeService):
    def __init__(self, compose_file_path, config_file_path, container_name):
        super().__init__(compose_file_path, container_name)
        self.parsed_compose_file = services.compose_parser.ServiceYmlParser(
            compose_file_path)
        port = self.parsed_compose_file.exposed_port
        self.endpoint = ('localhost', port)
        self.req_url = "http://{0}:{1}/api".format(
            self.endpoint[0], self.endpoint[1])
        self.config_file_path = config_file_path
        self.container_name = container_name
        self.last_vol_conf = None

    def request(self, method, endpoint, api_key=None, headers=None, *kargs, **kwargs):
        if headers is None:
            headers = {}

        if api_key is not None:
            headers[API_KEY_HEADER] = api_key

        if 'data' in kwargs and isinstance(kwargs['data'], dict):
            kwargs['data'] = json.dumps(kwargs['data'])

        return getattr(requests, method)(
            url='{0}/{1}'.format(self.req_url, endpoint), headers=headers, *kargs, **kwargs)

    def get(self, endpoint, *kargs, **kwargs):
        return self.request('get', endpoint, *kargs, **kwargs)

    def put(self, endpoint, data, *kargs, **kwargs):
        return self.request('put', endpoint, data=data, *kargs, **kwargs)

    def post(self, endpoint, *kargs, **kwargs):
        return self.request('post', endpoint, *kargs, **kwargs)

    def delete(self, endpoint, *kargs, **kwargs):
        return self.request('delete', endpoint, *kargs, **kwargs)

    def version(self):
        return self.get('version', timeout=15)

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
        return result.status_code == 200, str(result)

    def is_up(self):
        return self._is_service_alive()

    def _is_service_alive(self):
        try:
            self.trigger_check_registered()
            r = self.version()
            return r.status_code == 200
        except:
            return False

    @property
    def conf(self):
        return axonius.ConfigReader.PluginConfig(self.config_file_path)

    @property
    def vol_conf(self):
        # Try to get the latest, but if the container is down, use the last data.
        (out, _, _) = self.get_file_contents_from_container(VOLATILE_CONFIG_PATH)
        self.last_vol_conf = axonius.ConfigReader.PluginVolatileConfig(out.decode("utf-8"))

        return self.last_vol_conf

    @property
    def api_key(self):
        return self.vol_conf.api_key

    @property
    def unique_name(self):
        return self.vol_conf.unique_name


class AdapterService(PluginService):
    def __init__(self, compose_file_path, config_file_path, container_name):
        super().__init__(compose_file_path=compose_file_path, config_file_path=config_file_path,
                         container_name=container_name)

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

    @property
    def conf(self):
        return axonius.ConfigReader.AdapterConfig(self.config_file_path)
