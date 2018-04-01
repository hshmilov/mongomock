import json
import requests
import os
from cryptography.fernet import Fernet

from axonius.config_reader import PluginConfig, PluginVolatileConfig, AdapterConfig
from axonius.plugin_base import VOLATILE_CONFIG_PATH
from axonius.utils.files import CONFIG_FILE_NAME
from axonius.utils.json import from_json
from services.debug_template import py_charm_debug_template, py_charm_debug_port_template
from services.docker_service import DockerService
from services.ports import DOCKER_PORTS

API_KEY_HEADER = "x-api-key"
UNIQUE_KEY_PARAM = "unique_name"


class PluginService(DockerService):
    def __init__(self, container_name, service_dir=None):
        if service_dir is None:
            service_dir = f'../plugins/{container_name.replace("-", "_")}'
        super().__init__(container_name, service_dir)
        if self.container_name not in DOCKER_PORTS:
            raise ValueError(f'Container {self.container_name} missing external port in DOCKER_PORTS')
        self.endpoint = ('localhost', DOCKER_PORTS[self.container_name])
        self.req_url = "http://{0}:{1}/api".format(self.endpoint[0], self.endpoint[1])
        self.config_file_path = self.service_dir + '/' + CONFIG_FILE_NAME
        self.last_vol_conf = None
        if not self.service_class_name.endswith('Adapter'):
            self.service_class_name += 'Service'

    @property
    def volumes_override(self):
        libs = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'plugins',
                                            'axonius-libs', 'src', 'libs'))
        return [f'{self.service_dir}:/home/axonius/app/{self.package_name}:ro', f'{libs}:/home/axonius/libs:ro']

    def request(self, method, endpoint, api_key=None, headers=None, session=None, *vargs, **kwargs):
        if headers is None:
            headers = {}

        if api_key is not None:
            headers[API_KEY_HEADER] = api_key

        if 'data' in kwargs and isinstance(kwargs['data'], dict):
            kwargs['data'] = json.dumps(kwargs['data'])

        if session:
            with session:
                return session.request(method, url='{0}/{1}'.format(self.req_url, endpoint),
                                       headers=headers, *vargs, **kwargs)

        return requests.request(method, url='{0}/{1}'.format(self.req_url, endpoint),
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

    def assert_plugin_state(self, wanted_state):
        if wanted_state == 'enabled':
            wanted_status = 200
        elif wanted_state == 'disabled':
            wanted_status = 405
        else:
            raise ValueError("Unrecognized state")

        response = self.get('plugin_state')
        assert response.status_code == 200
        assert wanted_state == response.json()['state']

        # Validate on common endpoint
        self.version()
        assert self.get('logger').status_code == wanted_status

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
        raise NotImplementedError("TBD!")

    def action_update(self, action_id):
        raise NotImplementedError("TBD!")

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

    @property
    def plugin_name(self):
        return self.conf.name

    def generate_debug_template(self):
        name = self.adapter_name.replace("-", "_") if isinstance(self, AdapterService) else self.package_name
        ports = '\n'.join([py_charm_debug_port_template.format(host_port=host_port, internal_port=internal_port)
                           for host_port, internal_port in self.exposed_ports])
        output = py_charm_debug_template.format(name=name, container_name=self.container_name, ports=ports,
                                                run_type='adapters' if isinstance(self, AdapterService) else 'plugins')
        path = os.path.join(os.path.dirname(__file__), '..', '..', '.idea', 'runConfigurations', name + '_debug.xml')
        open(path, 'w').write(output)


class AdapterService(PluginService):

    def __init__(self, name: str):
        super().__init__(f'{name}-adapter', f'../adapters/{name.replace("-", "_")}_adapter')
        self.adapter_name = name

    def encrypt(self, encryption_key, to_encrypt):
        cipher = Fernet(encryption_key)
        return cipher.encrypt(bytes(to_encrypt, 'utf-8')).decode("utf-8")

    def add_client(self, client_details):
        from services.core_service import CoreService
        client_details_copy = dict(client_details)

        # Encrypting password format client details.
        schema = self.schema('clients').json()
        for item in schema['items']:
            if item.get('format', '') == 'password':
                client_details_copy[item['name']] = self.encrypt(CoreService().vol_conf.password_secret(),
                                                                 client_details_copy[item['name']])

        self.clients(client_details_copy)

    def users(self):
        response = requests.get(self.req_url + "/users", headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, str(response)
        return response.json()

    def devices(self):
        response = requests.get(self.req_url + "/devices", headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, str(response)
        return from_json(response.content)

    def trigger_clean_db(self):
        response = requests.post(self.req_url + "/clean_devices", headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, str(response)
        return from_json(response.content)

    def clients(self, client_data=None):
        if not client_data:
            response = requests.post(self.req_url + "/clients", headers={API_KEY_HEADER: self.api_key})
        else:
            response = requests.put(self.req_url + "/clients", headers={API_KEY_HEADER: self.api_key},
                                    json=client_data)
        assert response.status_code == 200, str(response)
        return response.json()

    def action(self, action_type):
        raise NotImplementedError("TBD!")

    def schema(self, schema_type="general", api_key=None):
        return self.get('{0}/{1}'.format('schema', schema_type), api_key=self.api_key if api_key is None else api_key)

    def is_up(self):
        return super().is_up() and "Adapter" in self.get_supported_features()

    @property
    def conf(self):
        return AdapterConfig(self.config_file_path)
