import requests
import traceback

from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS_COLLECTION, GUI_NAME, GUI_SYSTEM_CONFIG_COLLECTION
from axonius.consts.core_consts import CORE_CONFIG_NAME
from services.plugin_service import PluginService, API_KEY_HEADER, UNIQUE_KEY_PARAM


class CoreService(PluginService):
    def __init__(self):
        super().__init__('core')

    @property
    def get_max_uwsgi_threads(self) -> int:
        return 2000  # core serves as a proxy

    def _migrate_db(self):
        super()._migrate_db()
        if self.db_schema_version < 1:
            self._update_schema_version_1()

        if self.db_schema_version != 1:
            print(f'Upgrade failed, db_schema_version is {self.db_schema_version}')

    def _update_schema_version_1(self):
        print('Upgrade to schema 1')
        try:
            config_match = {
                'config_name': CORE_CONFIG_NAME
            }
            config_collection = self.db.get_collection(self.plugin_name, CONFIGURABLE_CONFIGS_COLLECTION)
            current_config = config_collection.find_one(config_match)
            if current_config:
                maintenance_config = current_config['config'].get('maintenance_settings')
                if maintenance_config:
                    self.db.get_collection(GUI_NAME, GUI_SYSTEM_CONFIG_COLLECTION).insert_one({
                        'type': 'maintenance',
                        'provision': maintenance_config.get('analytics', True),
                        'analytics': maintenance_config.get('analytics', True),
                        'troubleshooting': maintenance_config.get('troubleshooting', True),
                        'timeout': None
                    })
                del current_config['config']['maintenance_settings']
                config_collection.replace_one(config_match, current_config)
            self.db_schema_version = 1
        except Exception as e:
            print(f'Exception while upgrading core db to version 1. Details: {e}')
            traceback.print_exc()

    def register(self, api_key=None, plugin_name=""):
        headers = {}
        params = {}
        if api_key:
            headers[API_KEY_HEADER] = api_key
            params[UNIQUE_KEY_PARAM] = plugin_name

        return requests.get(self.req_url + "/register", headers=headers, params=params)

    def _is_service_alive(self):
        try:
            r = self.version()
            return r.status_code == 200
        except Exception:
            return False

    def get_registered_plugins(self):
        return self.register()

    def set_config(self, config):
        self.db.get_collection('core', CONFIGURABLE_CONFIGS_COLLECTION).update_one(
            {'config_name': CORE_CONFIG_NAME},
            {'$set': config}
        )
        self.post('update_config')
