import requests
from retrying import retry
from axonius.consts.scheduler_consts import Phases, SchedulerState
from services.plugin_service import PluginService, API_KEY_HEADER
from services.updatable_service import UpdatablePluginMixin

DEAFULT_SYSTEM_RESEARCH_RATE = 12
DEAFULT_SYSTEM_RESEARCH_RATE_ATTRIB_NAME = 'system_research_rate'
DEAFULT_SYSTEM_RESEARCH_DATE_TIME = '13:00'
DEFAULT_SYSTEM_RESEARCH_DATE_ATTRIB_NAME_MAIN = 'system_research_date'
DEAFULT_SYSTEM_RESEARCH_DATE_ATTRIB_NAME = 'system_research_date_time'
DEAFULT_SYSTEM_RESEARCH_DATE_RECURRENCE = '1'
DEAFULT_SYSTEM_RESEARCH_DATE_RECURRENCE_ATTRIB_NAME = 'system_research_date_recurrence'
DEFAULT_SYSTEM_SAVE_HISTORY = True
DEFAULT_SYSTEM_SAVE_HISTORY_ATTRIB_NAME = 'save_history'
DEFAULT_SYSTEM_RESEARCH_MODE = DEAFULT_SYSTEM_RESEARCH_RATE_ATTRIB_NAME
DEFAULT_SYSTEM_RESEARCH_MODE_ATTRIB_NAME = 'conditional'


class SystemSchedulerService(PluginService, UpdatablePluginMixin):
    def __init__(self):
        super().__init__('system-scheduler')

    def stop_research(self):
        response = requests.post(
            self.req_url + '/stop_all', headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f'Error in response: {str(response.status_code)}, ' \
                                            f'{str(response.content)}'
        return response

    def start_research(self):
        response = requests.post(
            self.req_url + '/trigger/execute?blocking=False', headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f'Error in response: {str(response.status_code)}, ' \
                                            f'{str(response.content)}'
        return response

    def current_state(self):
        response = requests.get(
            self.req_url + '/state', headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f'Error in response: {str(response.status_code)}, ' \
                                            f'{str(response.content)}'
        return response

    def trigger_s3_backup(self):
        response = requests.get(
            self.req_url + '/trigger_s3_backup', headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f'Error in response: {str(response.status_code)}, ' \
            f'{str(response.content)}'
        return response

    def trigger_root_master_s3_restore(self):
        response = requests.get(
            self.req_url + '/trigger_root_master_s3_restore', headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, f'Error in response: {str(response.status_code)}, ' \
            f'{str(response.content)}'
        return response

    @retry(stop_max_attempt_number=300, wait_fixed=1000)
    def wait_for_scheduler(self, is_scheduler_at_rest: bool):
        """
        Waits until scheduler is running or not running or raises
        """
        if is_scheduler_at_rest:
            requests.get(self.req_url + '/wait/execute', headers={API_KEY_HEADER: self.api_key}).raise_for_status()
            return

        scheduler_state = self.current_state().json()
        state = SchedulerState(**scheduler_state['state'])
        assert state.Phase != Phases.Stable.name

    def _migrate_db(self):
        super()._migrate_db()
        # Do not change this to 1.
        if self.db_schema_version < 2:
            self._update_schema_version_2()
        if self.db_schema_version < 3:
            self._update_schema_version_3()

        if self.db_schema_version != 3:
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

            system_research_rate = current_config.get(DEAFULT_SYSTEM_RESEARCH_RATE_ATTRIB_NAME,
                                                      DEAFULT_SYSTEM_RESEARCH_RATE)
            save_history = current_config.get(DEFAULT_SYSTEM_SAVE_HISTORY_ATTRIB_NAME,
                                              DEFAULT_SYSTEM_SAVE_HISTORY)

            config_collection.replace_one(
                {
                    'config_name': 'SystemSchedulerService'
                },
                {
                    'config_name': 'SystemSchedulerService',
                    'config': {
                        'discovery_settings': {
                            DEAFULT_SYSTEM_RESEARCH_RATE_ATTRIB_NAME: system_research_rate,
                            DEFAULT_SYSTEM_SAVE_HISTORY_ATTRIB_NAME: save_history
                        }
                    }
                }
            )

        except Exception as e:
            print(f'Exception while upgrading scheduler db to version 2. Details: {e}')
        finally:
            print('Upgraded system scheduler to version 2')
            self.db_schema_version = 2

    def _update_schema_version_3(self):
        print('upgrade to schema 3')
        try:
            config_collection = self.db.get_collection(self.plugin_name, 'configurable_configs')
            config_match = {
                'config_name': 'SystemSchedulerService'
            }
            current_config = config_collection.find_one(config_match)
            if not current_config:
                print('No config present - continue')
                return

            current_config = current_config.get('config')
            if not current_config:
                print(f'Weird config - continue ({current_config})')
                return

            current_config = current_config.get('discovery_settings')

            if not current_config:
                print(f'Weird discovery_settings - continue ({current_config})')
                return

            system_research_date_time = current_config.get(DEFAULT_SYSTEM_RESEARCH_DATE_ATTRIB_NAME_MAIN,
                                                           DEAFULT_SYSTEM_RESEARCH_DATE_TIME)

            config_collection.update_one(config_match,
                                         {
                                             '$set': {
                                                 f'config.discovery_settings.{DEFAULT_SYSTEM_RESEARCH_DATE_ATTRIB_NAME_MAIN}': {
                                                     DEAFULT_SYSTEM_RESEARCH_DATE_ATTRIB_NAME: system_research_date_time,
                                                     DEAFULT_SYSTEM_RESEARCH_DATE_RECURRENCE_ATTRIB_NAME:
                                                     DEAFULT_SYSTEM_RESEARCH_DATE_RECURRENCE
                                                 }
                                             }
                                         }
                                         )

        except Exception as e:
            print(f'Exception while upgrading scheduler db to version 3. Details: {e}')
        finally:
            print('Upgraded system scheduler to version 3')
            self.db_schema_version = 3
