import json
import os
import time
from typing import Dict

import gridfs
import requests
from bson import ObjectId
from pymongo.collection import Collection

from axonius.config_reader import (AdapterConfig, PluginConfig,
                                   PluginVolatileConfig)
from axonius.consts.plugin_consts import (CONFIGURABLE_CONFIGS_COLLECTION,
                                          VERSION_COLLECTION)
from axonius.entities import EntityType
from axonius.plugin_base import VOLATILE_CONFIG_PATH
from axonius.utils.files import CONFIG_FILE_NAME
from axonius.utils.json import from_json
from services.debug_template import (py_charm_debug_port_template,
                                     py_charm_debug_template)
from services.plugins.mongo_service import MongoService
from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService
from test_helpers.file_mock_credentials import FileForCredentialsMock
from test_helpers.log_tester import LogTester

API_KEY_HEADER = "x-api-key"
UNIQUE_KEY_PARAM = "unique_name"


class PluginService(WeaveService):
    def __init__(self, container_name, service_dir=None):
        if service_dir is None:
            service_dir = f'../plugins/{container_name.replace("-", "_")}'
        super().__init__(container_name, service_dir)
        if self.container_name not in DOCKER_PORTS:
            raise ValueError(f'Container {self.container_name} missing external port in DOCKER_PORTS')
        self.endpoint = ('localhost', DOCKER_PORTS[self.container_name])
        self.req_url = "https://{0}:{1}/api".format(self.endpoint[0], self.endpoint[1])
        self.config_file_path = self.service_dir + '/' + CONFIG_FILE_NAME
        self.last_vol_conf = None
        if not self.service_class_name.endswith('Adapter'):
            self.service_class_name += 'Service'
        self.plugin_name = os.path.basename(self.service_dir)
        self.db = MongoService()
        self.__cached_api_key = None

        self._historical_entity_views_db_map: Dict[EntityType, Collection] = {
            EntityType.Users: self.db.client['aggregator']['historical_users_db_view'],
            EntityType.Devices: self.db.client['aggregator']['historical_devices_db_view'],
        }

        self._entity_db_map: Dict[EntityType, Collection] = {
            EntityType.Users: self.db.client['aggregator']['users_db'],
            EntityType.Devices: self.db.client['aggregator']['devices_db'],
        }

    @property
    def volumes_override(self):
        libs = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'axonius-libs', 'src', 'libs'))
        return [f'{self.service_dir}:/home/axonius/app/{self.package_name}', f'{libs}:/home/axonius/libs:ro']

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

    def get_supported_features(self):
        res = self.get('supported_features', timeout=15)
        assert res.status_code == 200
        return set(res.json())

    def trigger_check_registered(self):
        try:
            # Will trigger the plugin to check if he is registered. If not, the plugin will exit immediately
            self.get('trigger_registration_check', timeout=15)
        except Exception:
            pass

    def is_plugin_registered(self, core_service):
        unique_name = self.unique_name
        result = core_service.register(self.api_key, unique_name)
        return result.status_code == 200

    def trigger_execute(self, blocking: bool):
        response = requests.post(
            self.req_url + f'/trigger/execute?blocking={blocking}',
            headers={API_KEY_HEADER: self.api_key}
        )

        assert response.status_code == 200, \
            f'Error in response: {str(response.status_code)}, ' \
            f'{str(response.content)}'

        return response

    def is_up(self):
        return self._is_service_alive() and "Plugin" in self.get_supported_features()

    def _is_service_alive(self):
        try:
            self.trigger_check_registered()
            r = self.version()
            return r.status_code == 200
        except Exception:
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
        if self.__cached_api_key is not None:
            return self.__cached_api_key
        self.__cached_api_key = self.vol_conf.api_key
        return self.__cached_api_key

    @property
    def unique_name(self):
        return self.vol_conf.unique_name

    @property
    def log_path(self):
        return os.path.join(self.log_dir, f'{self.unique_name}.axonius.log')

    @property
    def log_tester(self):
        return LogTester(self.log_path)

    def generate_debug_template(self):
        name = self.adapter_name.replace("-", "_") if isinstance(self, AdapterService) else self.package_name
        ports = '\n'.join([py_charm_debug_port_template.format(host_port=host_port, internal_port=internal_port)
                           for host_port, internal_port in self.exposed_ports])
        output = py_charm_debug_template.format(name=name, container_name=self.container_name, ports=ports,
                                                run_type='adapters' if isinstance(self, AdapterService) else 'plugins')
        path = os.path.join(os.path.dirname(__file__), '..', '..', '.idea', 'runConfigurations', name + '_debug.xml')
        open(path, 'w').write(output)

    def get_configurable_config(self, conf_name: str) -> dict:
        """
        Reads a specific config from 'configs'. Used with conjugation with Configurable (mixin).
        If Configurable isn't implemented for this plugin or the conf_name doesn't exists - returns None.
        Otherwise, returns the configuration
        :param conf_name: The class name of the config to return
        :return: the config or None
        """
        config_bulk = self.db.client[self.unique_name][CONFIGURABLE_CONFIGS_COLLECTION].find_one({
            'config_name': conf_name})
        if config_bulk:
            return config_bulk.get('config')
        return None

    def set_configurable_config(self, conf_name: str, specific_key: str, value=None):
        """
        Write a specific config from 'configs'. Used with conjugation with Configurable (mixin).
        If Configurable isn't implemented for this plugin or the conf_name doesn't exists - returns None.
        Otherwise, returns the configuration
        :param conf_name: The class name of the config to return
        :param specific_key
        :param value
        :return: the config or None
        """
        config_bulk = self.db.client[self.unique_name][CONFIGURABLE_CONFIGS_COLLECTION].find_one({
            'config_name': conf_name})
        config_bulk = config_bulk['config']
        config_bulk[specific_key] = value
        self.db.client[self.unique_name][CONFIGURABLE_CONFIGS_COLLECTION].update_one({'config_name': conf_name},
                                                                                     {"$set":
                                                                                      {f"config."
                                                                                       f"{specific_key}": value}})
        response = requests.post(self.req_url + "/update_config", headers={API_KEY_HEADER: self.api_key})
        response.raise_for_status()

    @property
    def __version_collection(self):
        return self.db.get_collection(self.plugin_name, VERSION_COLLECTION)

    @property
    def self_database(self):
        return self.db.client[self.unique_name]

    @property
    def db_schema_version(self):
        res = self.__version_collection.find_one({'name': 'schema'})
        if not res:
            return 0
        return res.get('version', 0)

    @db_schema_version.setter
    def db_schema_version(self, val):
        self.__version_collection.replace_one({'name': 'schema'},
                                              {'name': 'schema', 'version': val},
                                              upsert=True)

    def get_file_content_from_db(self, uuid):
        oid = ObjectId(uuid)
        return gridfs.GridFS(self.db.client[self.unique_name]).get(oid).read()


class AdapterService(PluginService):

    def __init__(self, name: str):
        super().__init__(f'{name}-adapter', f'../adapters/{name.replace("-", "_")}_adapter')

    @property
    def adapter_name(self):
        return self.service_name[:-len('_adapter')]

    def add_client(self, client_details):
        return self.clients(client_details)

    def users(self):
        response = requests.get(self.req_url + "/users", headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, str(response)
        return response.json()

    def devices(self):
        response = requests.get(self.req_url + "/devices", headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, str(response)
        return from_json(response.content)

    def trigger_clean_db(self):
        # This help guarantee consistency for transactions
        time.sleep(1)
        response = requests.post(self.req_url + "/trigger/clean_devices?priority=True",
                                 headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, str(response)
        return from_json(response.content)

    def _process_clients_for_adapter(self, client_data):
        if isinstance(client_data, dict):
            client_data = {k: self._process_clients_for_adapter(v) for k, v in client_data.items()}
            return client_data
        if isinstance(client_data, list):
            client_data = [self._process_clients_for_adapter(x) for x in client_data]
            return client_data
        if isinstance(client_data, FileForCredentialsMock):
            import gridfs
            fs = gridfs.GridFS(self.db.client[self.unique_name])
            if isinstance(client_data.file_contents, str):
                written_file = fs.put(client_data.file_contents, filename=client_data.filename, encoding='utf8')
            else:
                written_file = fs.put(client_data.file_contents, filename=client_data.filename)
            return {"uuid": str(written_file), "filename": client_data.filename}
        return client_data

    def clients(self, client_data=None):
        if not client_data:
            response = requests.post(self.req_url + "/clients", headers={API_KEY_HEADER: self.api_key})
        else:
            client_data = self._process_clients_for_adapter(client_data)
            response = requests.put(self.req_url + "/clients", headers={API_KEY_HEADER: self.api_key},
                                    json=client_data)
        assert response.status_code == 200, str(response)
        return response.json()

    def is_client_reachable(self, client_data):
        client_data = self._process_clients_for_adapter(client_data)
        response = requests.post(self.req_url + "/client_test", headers={API_KEY_HEADER: self.api_key},
                                 json=client_data)

        return response.status_code == 200

    def action(self, action_type):
        pass

    def schema(self, schema_type="general", api_key=None):
        return self.get('{0}/{1}'.format('schema', schema_type), api_key=self.api_key if api_key is None else api_key)

    def is_up(self):
        return super().is_up() and "Adapter" in self.get_supported_features()

    @property
    def conf(self):
        return AdapterConfig(self.config_file_path)
