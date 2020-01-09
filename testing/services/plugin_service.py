import base64
import importlib
import json
import os
import shlex
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Type, Any

import cachetools
import gridfs
import requests
from axonius.adapter_base import AdapterBase

from bson import ObjectId
from pymongo.collection import Collection
from retrying import retry

from axonius.config_reader import (AdapterConfig, PluginConfig,
                                   PluginVolatileConfig)
from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS_COLLECTION, PLUGIN_UNIQUE_NAME, CORE_UNIQUE_NAME, \
    PLUGIN_NAME, NODE_ID, LIBS_PATH, KEYS_COLLECTION
from axonius.consts.system_consts import AXONIUS_DNS_SUFFIX, WEAVE_NETWORK, WEAVE_PATH, DB_KEY_PATH
from axonius.entities import EntityType
from axonius.plugin_base import VOLATILE_CONFIG_PATH
from axonius.utils.encryption import mongo_encrypt
from axonius.utils.files import CONFIG_FILE_NAME
from axonius.utils.json import from_json
from axonius.utils.threading import singlethreaded
from services.debug_template import (py_charm_debug_port_template,
                                     py_charm_debug_template,
                                     py_charm_debug_volumes_template,
                                     py_charm_debug_volumes_template_gui_service)
from services.plugins.mongo_service import MongoService
from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService
from test_helpers.exceptions import DockerException
from test_helpers.file_mock_credentials import FileForCredentialsMock
from test_helpers.log_tester import LogTester

API_KEY_HEADER = "x-api-key"
UNIQUE_KEY_PARAM = "unique_name"
WEAVE_API_URL = 'http://127.0.0.1:6784'


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
        if self.container_name == CORE_UNIQUE_NAME:
            self.core = self
        else:
            from services.plugins.core_service import CoreService
            self.core = CoreService()

        self.core_configs_collection = self.db.client[CORE_UNIQUE_NAME]['configs']
        self.__cached_api_key = None
        self.__cached_unique_name = None

        self._historical_entity_views_db_map: Dict[EntityType, Collection] = {
            EntityType.Users: self.db.client['aggregator']['historical_users_db_view'],
            EntityType.Devices: self.db.client['aggregator']['historical_devices_db_view'],
        }

        self._entity_db_map: Dict[EntityType, Collection] = {
            EntityType.Users: self.db.client['aggregator']['users_db'],
            EntityType.Devices: self.db.client['aggregator']['devices_db'],
        }

        self._entity_views_map: Dict[EntityType, Collection] = {
            EntityType.Users: self.db.client['gui']['user_views'],
            EntityType.Devices: self.db.client['gui']['device_views'],
        }

    def __ask_core_to_raise_adapter(self, plugin_unique_name: str):
        print(f'asking core to raise {plugin_unique_name}')
        if 'adapter' not in plugin_unique_name:
            # Only adapters can be down like this
            return
        self.core.trigger(job_name=f'start:{plugin_unique_name}', blocking=True, reschedulable=False)

    def _verify_plugin_is_up(self, plugin_unique_name: str):
        if plugin_unique_name == CORE_UNIQUE_NAME:
            # Core is assumed to be up
            return
        if 'adapter' not in plugin_unique_name:
            # Only adapters can be down like this
            return

        plugin_data = self.core_configs_collection.find_one({
            PLUGIN_UNIQUE_NAME: plugin_unique_name
        }, projection={
            '_id': 0,
            'status': 1,
        })
        if not plugin_data:
            raise RuntimeError(f'Plugin {plugin_unique_name} not found!')

        if plugin_data['status'] != 'up':
            # asking core to raise adapter
            self.__ask_core_to_raise_adapter(plugin_unique_name)

        return True

    @property
    def volumes_override(self):
        libs = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'axonius-libs', 'src', 'libs'))
        return [f'{self.service_dir}:/home/axonius/app/{self.package_name}', f'{libs}:{LIBS_PATH.as_posix()}:ro']

    @property
    def should_register_unique_dns(self):
        return True

    def __perform_request(self, method, endpoint, headers, session, *vargs, **kwargs):
        """
        See request
        """
        if session:
            with session:
                return session.request(method, url='{0}/{1}'.format(self.req_url, endpoint),
                                       headers=headers, *vargs, **kwargs)

        return requests.request(method, url='{0}/{1}'.format(self.req_url, endpoint),
                                headers=headers, *vargs, **kwargs)

    def request(self, method, endpoint, api_key=None, headers=None, session=None, *vargs, verify_is_up: bool = True,
                **kwargs):
        if verify_is_up:
            self._verify_plugin_is_up(self.unique_name)
        if headers is None:
            headers = {}

        if api_key is not None:
            headers[API_KEY_HEADER] = api_key

        headers['x-unique-plugin-name'] = self.unique_name
        headers['x-plugin-name'] = self.plugin_name

        if 'data' in kwargs and isinstance(kwargs['data'], dict):
            kwargs['data'] = json.dumps(kwargs['data'])
        try:
            return self.__perform_request(method, endpoint, headers, session, *vargs, **kwargs)
        except Exception:
            if verify_is_up:
                self.__ask_core_to_raise_adapter(self.unique_name)
                return self.__perform_request(method, endpoint, headers, session, *vargs, **kwargs)
            raise

    def get(self, endpoint, *vargs, **kwargs):
        return self.request('get', endpoint, *vargs, **kwargs)

    def put(self, endpoint, data=None, *vargs, **kwargs):
        return self.request('put', endpoint, data=data, *vargs, **kwargs)

    def post(self, endpoint, *vargs, **kwargs):
        return self.request('post', endpoint, *vargs, **kwargs)

    def delete(self, endpoint, *vargs, **kwargs):
        return self.request('delete', endpoint, *vargs, **kwargs)

    def version(self):
        return self.get('version', timeout=15)

    def get_supported_features(self, *args, **kwargs):
        res = self.get('supported_features', timeout=15, *args, **kwargs)
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

    def is_unique_dns_registered(self):
        if self.docker_network == WEAVE_NETWORK:
            return super().is_unique_dns_registered()
        else:
            return self.fqdn in self.inspect[0]['NetworkSettings']['Networks']['axonius']['Aliases']

    def trigger(self, job_name: str, blocking: bool, reschedulable: bool = True, post_json: dict = None):
        response = self.post(f'/trigger/{job_name}?blocking={blocking}&reschedulable={reschedulable}',
                             headers={
                                 API_KEY_HEADER: self.api_key
                             }, json=post_json)
        assert response.status_code == 200, \
            f'Error in response: {str(response.status_code)}, ' \
            f'{str(response.content)}'

        return response

    def trigger_execute(self, blocking: bool):
        self.trigger('execute', blocking)

    def is_up(self, *args, **kwargs):
        return self._is_service_alive() and "Plugin" in self.get_supported_features()

    @property
    def fqdn(self):
        try:
            return f'{self.unique_name}.{AXONIUS_DNS_SUFFIX}'
        except DockerException:
            return super().fqdn

    def start_and_wait(self, **kwargs):
        super().start_and_wait(**kwargs)
        self.register_unique_dns()
        self.api_key  # put API key in cache
        self.unique_name  # put unique name in cache

    @retry(stop_max_attempt_number=3, wait_fixed=5)
    def register_unique_dns(self):
        # Notice that we still register names like 'static-correlator', in which the service name is the same
        # as the adapters name, since the dns resolving otherwise sometimes does not work.

        if self.docker_network == WEAVE_NETWORK:
            # Remove old dns entry from weave
            dns_remove_command = shlex.split(f'{WEAVE_PATH} dns-remove {self.id}')
            subprocess.check_call(dns_remove_command)

            # Check that we have removed the dns entries. If we still have a dns entry associated with that hostname,
            # it must be an old dead container. see:
            # * https://github.com/weaveworks/weave/issues/3432
            # * https://axonius.atlassian.net/browse/AX-4731
            dns_check_command = shlex.split(f'{WEAVE_PATH} dns-lookup {self.fqdn}')
            response = subprocess.check_output(dns_check_command).strip().decode('utf-8')

            if response:
                # We should not have any other ip associated with this hostname. Lets remove it.
                for ip in response.splitlines():
                    print(f'Found stale weave-dns record: {self.fqdn} -> {ip}. Removing')
                    for _ in range(3):
                        # Try 3 times, because weave is not always working
                        requests.delete(f'{WEAVE_API_URL}/name/*/{ip.strip()}?fqdn={self.fqdn}')
                        # We do not raise for status or fail, as this is too risky.

            # Add new unique dns entry to weave
            dns_add_command = shlex.split(
                f'{WEAVE_PATH} dns-add {self.id} -h {self.fqdn}')

            subprocess.check_call(dns_add_command)

            dns_check_command = shlex.split(f'{WEAVE_PATH} dns-lookup {self.fqdn}')
            response = subprocess.check_output(dns_check_command).strip()
            if not response:
                print(f'Error looking up dns {self.fqdn}. Retrying...', file=sys.stderr)
                raise ValueError(f'Error looking up dns {self.fqdn} after registration.')
        else:
            # Remove container with old dns entry from network
            disconnect_to_network_command = f'docker network disconnect {self.docker_network} {self.container_name}'
            subprocess.check_call(shlex.split(disconnect_to_network_command))

            # Add container with new unique dns entry to network
            connect_to_network_command = \
                f'docker network connect --alias {self.fqdn} {self.docker_network} {self.container_name}'
            subprocess.check_call(shlex.split(connect_to_network_command))

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
        try:
            self.__cached_api_key = self.vol_conf.api_key
        except Exception:
            # If the plugin is down, or anything, give something else
            return self.db.client['core']['configs'].find_one({})['api_key']
        return self.__cached_api_key

    @property
    def unique_name(self):
        try:
            self.__cached_unique_name = self.vol_conf.unique_name
        except Exception:
            # If the plugin is down, getting the unique name will fail.
            # in this case, use the cache
            if self.__cached_unique_name is not None:
                return self.__cached_unique_name
            else:
                # If there's no cache, die. This shouldn't happened.
                raise
        return self.__cached_unique_name

    @property
    def log_path(self):
        return os.path.join(self.log_dir, f'{self.unique_name}.axonius.log')

    @property
    def log_tester(self):
        return LogTester(self.log_path)

    def generate_debug_template(self, db_key=None, node_id=None):

        name = self.adapter_name.replace('-', '_') if isinstance(self, AdapterService) else self.package_name
        ports = '\n'.join([py_charm_debug_port_template.format(host_port=host_port, internal_port=internal_port)
                           for host_port, internal_port in self.exposed_ports])

        run_type = 'adapters' if isinstance(self, AdapterService) else 'plugins'

        volumes = (py_charm_debug_volumes_template_gui_service.format(run_type=run_type,
                                                                      container_name=self.container_name)
                   if name == 'gui'
                   else py_charm_debug_volumes_template.format(run_type=run_type, container_name=self.container_name))

        output = py_charm_debug_template.format(name=name,
                                                container_name=self.container_name,
                                                ports=ports,
                                                db_key=db_key,
                                                node_id=node_id,
                                                volumes=volumes,
                                                run_type=run_type)

        path = Path(__file__).parents[2] / ('.idea/runConfigurations/' + name + '_debug.xml')
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
        self._verify_plugin_is_up(self.unique_name)
        response = requests.post(self.req_url + "/update_config", headers={API_KEY_HEADER: self.api_key})
        response.raise_for_status()

    @property
    def self_database(self):
        return self.db.client[self.unique_name]

    @singlethreaded()
    @cachetools.cached(cachetools.LRUCache(maxsize=1), lock=threading.Lock())
    def get_db_encryption_key(self) -> bytes:
        """
        Get db encryption key from DB_KEY_PATH file
        :return: encryption key data
        """
        if DB_KEY_PATH.is_file():
            b64_key = DB_KEY_PATH.read_text().strip()
            return base64.b64decode(b64_key)

    def db_encrypt(self, plugin_unique_name: str, data_to_encrypt: Any) -> Any:
        """
        Encrypt data using mongoclient encryption
        :param plugin_unique_name: plugin unique name for encrypting its data
        :param data_to_encrypt: data to encrypt
        :return: encrypted data
        """
        enc = mongo_encrypt.get_db_encryption(
            self.db.client, KEYS_COLLECTION, self.get_db_encryption_key())
        encrypted = mongo_encrypt.db_encrypt(enc, plugin_unique_name, data_to_encrypt)
        return encrypted

    def db_decrypt(self, data_to_decrypt: Any) -> Any:
        """
        Decrypt data using mongo client encryption
        :param data_to_decrypt: data to decrypt
        :return: Decrypted data
        """
        enc_key = self.get_db_encryption_key()
        enc = mongo_encrypt.get_db_encryption(self.db.client, KEYS_COLLECTION, enc_key)
        decrypted = mongo_encrypt.db_decrypt(enc, data_to_decrypt)
        return decrypted

    def decrypt_dict(self, data: dict):
        """
        Decrypt dict values
        :param data: data to decrypt
        :return: None
        """
        for key, val in data.items():
            if val:
                data[key] = self.db_decrypt(val)

    def get_file_content_from_db(self, uuid):
        oid = ObjectId(uuid)
        return gridfs.GridFS(self.db.client[self.unique_name]).get(oid).read()

    def reload_uwsgi(self):
        response = self.get('/reload_uwsgi', headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 500, str(response)  # this is the legitimate response here

    @contextmanager
    def contextmanager(self, *, should_delete=True, take_ownership=False, allow_restart=True):
        with super().contextmanager(should_delete=should_delete,
                                    take_ownership=take_ownership,
                                    allow_restart=allow_restart):
            self.register_unique_dns()
            yield self


class AdapterService(PluginService):

    def __init__(self, name: str):
        super().__init__(f'{name}-adapter', f'../adapters/{name.replace("-", "_")}_adapter')

    @property
    def adapter_name(self):
        return self.service_name[:-len('_adapter')]

    def quick_register(self):
        """
        Performs a registration of this adapter without raising it
        """
        # Makes the logs dir for later
        Path(self.log_dir).mkdir(exist_ok=True)

        node_id = self.node_id

        additional_data = {}
        found_document = self.core_configs_collection.find_one({
            PLUGIN_NAME: self.plugin_name,
            NODE_ID: {
                # we want to fix all plugins with the given node_id
                # in some cases, node_id might have a leading exclamation mark, and we want to catch it too
                '$in': [node_id, f'!{node_id}']
            }
        })
        if found_document:
            # if this node_id&plugin_name exists, then re-register with the appropriate information
            print(f'Already registered as {found_document[PLUGIN_UNIQUE_NAME]}')
            additional_data[PLUGIN_UNIQUE_NAME] = found_document[PLUGIN_UNIQUE_NAME]
            additional_data['api_key'] = found_document['api_key']

        del found_document

        # Importing the actual python class for the plugin
        adapter_module = importlib.import_module(f'adapters.{self.package_name}.service')
        adapter_class: Type[AdapterBase] = getattr(adapter_module, self.service_class_name)

        class Empty:
            pass

        # Initializing an instance of the class without calling the constructor
        empty_instance: AdapterBase = Empty()
        empty_instance.__class__ = adapter_class

        # override internal DB client
        empty_instance.mongo_client = self.db.client

        # First, verify we have the schema and don't fail on getting it
        clients_schema = empty_instance._clients_schema()

        # Second, try to perform a registration with core, so it will actually show up in the list of adapters
        doc = {
            PLUGIN_NAME: self.plugin_name,
            'plugin_type': empty_instance.plugin_type,
            'plugin_subtype': empty_instance.plugin_subtype.value,
            'is_debug': False,
            'supported_features': list(empty_instance._Feature__supported_features()),
            NODE_ID: node_id,
            'quick_register': True,  # Implies this adapter isn't actually up,
            **additional_data
        }
        response = self.core.perform_quick_register(doc)
        response.raise_for_status()

        response_dict: dict = response.json()
        del response

        plugin_unique_name = response_dict[PLUGIN_UNIQUE_NAME]
        print(f'Quick registered to {plugin_unique_name}')
        empty_instance.plugin_unique_name = plugin_unique_name

        adapter_db = self.db.client[plugin_unique_name]

        adapter_db['adapter_schema'].replace_one({
            'adapter_name': plugin_unique_name
        }, {
            'adapter_name': plugin_unique_name,
            'adapter_version': '%version%',  # leftover
            'schema': clients_schema
        }, upsert=True)

        # Insert configurable to DB
        # If this fails, we need to actually raise the adapter
        print('Adding configurable')
        empty_instance._update_schema()

    def add_client(self, client_details):
        return self.clients(client_details)

    def users(self):
        response = self.get('/users', headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, str(response)
        return response.json()

    def devices(self):
        response = self.get('/devices', headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, str(response)
        return from_json(response.content)

    def trigger_clean_db(self):
        # This help guarantee consistency for transactions
        time.sleep(1)
        response = self.post('/trigger/clean_devices?priority=True',
                             headers={
                                 API_KEY_HEADER: self.api_key
                             })

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
            response = self.post('clients', headers={API_KEY_HEADER: self.api_key})
        else:
            client_data = self._process_clients_for_adapter(client_data)
            response = self.put('clients', headers={API_KEY_HEADER: self.api_key},
                                json=client_data)
        assert response.status_code == 200, str(response)
        return response.json()

    def is_client_reachable(self, client_data):
        client_data = self._process_clients_for_adapter(client_data)
        response = self.post('/client_test', headers={API_KEY_HEADER: self.api_key},
                             json=client_data)

        return response.status_code == 200

    def action(self, action_type):
        pass

    def schema(self, schema_type="general", api_key=None):
        return self.get('{0}/{1}'.format('schema', schema_type), api_key=self.api_key if api_key is None else api_key)

    def is_up(self, raise_via_core: bool = True):
        """
        Verifies the adapter is up
        :param raise_via_core: if False, will not try to raise via core
        """
        if raise_via_core:
            self._verify_plugin_is_up(self.unique_name)
        return "Adapter" in self.get_supported_features(verify_is_up=raise_via_core)

    @property
    def conf(self):
        return AdapterConfig(self.config_file_path)

    def trigger_insert_to_db(self, client_name: str, check_fetch_time: bool = True, blocking: bool = True):
        return self.trigger('insert_to_db', blocking=blocking, post_json={
            'client_name': client_name,
            'check_fetch_time': check_fetch_time
        })
