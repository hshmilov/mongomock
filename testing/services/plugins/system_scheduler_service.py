import requests
from retrying import retry
from axonius.consts.scheduler_consts import Phases, SchedulerState

from services.plugin_service import PluginService, API_KEY_HEADER


class SystemSchedulerService(PluginService):
    def __init__(self):
        super().__init__('system-scheduler')

    def stop_research(self):
        response = requests.post(
            self.req_url + "/stop_all", headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def start_research(self):
        response = requests.post(
            self.req_url + "/trigger/execute?blocking=False", headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    def current_state(self):
        response = requests.get(
            self.req_url + "/state", headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f"Error in response: {str(response.status_code)}, " \
                                            f"{str(response.content)}"
        return response

    @retry(stop_max_attempt_number=300, wait_fixed=1000)
    def wait_for_scheduler(self, is_scheduler_at_rest: bool):
        """
        Waits until scheduler is running or not running or raises
        """
        if is_scheduler_at_rest:
            requests.get(self.req_url + "/wait/execute", headers={API_KEY_HEADER: self.api_key}).raise_for_status()
            return

        scheduler_state = self.current_state().json()
        state = SchedulerState(**scheduler_state['state'])
        assert state.Phase != Phases.Stable.name

    def _migrate_db(self):
        super()._migrate_db()
        # Do not change this to 1.
        if self.db_schema_version < 2:
            self._update_schema_version_2()

        if self.db_schema_version != 2:
            print(f'Upgrade failed, db_schema_version is {self.db_schema_version}')

    def _update_schema_version_2(self):
        print('upgrade to schema 2')
        try:
            config_collection = self.db.get_collection(self.plugin_name, 'configurable_configs')
            current_config = config_collection.find_one({
                'config_name': 'SystemSchedulerService'
            })
            if not current_config:
                print('No config present - continue')
                return

            current_config = current_config.get('config')
            if not current_config:
                print(f'Weird config - continue ({current_config})')
                return

            system_research_rate = current_config.get('system_research_rate', 12)
            save_history = current_config.get('save_history', True)

            config_collection.replace_one(
                {
                    'config_name': 'SystemSchedulerService'
                },
                {
                    'config_name': 'SystemSchedulerService',
                    'config': {
                        'discovery_settings': {
                            'system_research_rate': system_research_rate,
                            'save_history': save_history
                        }
                    }
                }
            )

        except Exception as e:
            print(f'Exception while upgrading scheduler db to version 2. Details: {e}')
        finally:
            print('Upgraded system scheduler to version 2')
            self.db_schema_version = 2
