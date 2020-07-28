import requests
from pymongo.database import Database

from axonius.consts.plugin_consts import STATIC_USERS_CORRELATOR_PLUGIN_NAME
from axonius.db_migrations import db_migration

from services.plugin_service import API_KEY_HEADER, PluginService
from services.updatable_service import UpdatablePluginMixin


class StaticUsersCorrelatorService(PluginService, UpdatablePluginMixin):
    def __init__(self):
        super().__init__('static-users-correlator')

    def _migrate_db(self):
        super()._migrate_db()
        self._run_all_migrations(nonsingleton=True)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_1(self, specific_execution_db: Database):
        # Change execution to be a single instance, so we rename all collections over
        admin_db = self.db.client['admin']
        for collection_name in specific_execution_db.list_collection_names():
            admin_db.command({
                'renameCollection': f'{specific_execution_db.name}.{collection_name}',
                'to': f'{STATIC_USERS_CORRELATOR_PLUGIN_NAME}.{collection_name}'
            })

    def correlate(self, blocking: bool):
        response = requests.post(
            self.req_url + f'/trigger/execute?blocking={blocking}',
            headers={API_KEY_HEADER: self.api_key}
        )

        assert response.status_code == 200, \
            f'Error in response: {str(response.status_code)}, ' \
            f'{str(response.content)}'

        return response
