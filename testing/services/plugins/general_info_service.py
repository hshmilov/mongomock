import pytest
from pymongo.database import Database

from axonius.consts.plugin_consts import GENERAL_INFO_PLUGIN_NAME
from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture
from services.triggerable_service import TriggerableServiceMixin
from services.updatable_service import UpdatablePluginMixin


class GeneralInfoService(PluginService, TriggerableServiceMixin, UpdatablePluginMixin):
    def __init__(self):
        super().__init__('general-info')

    def _migrate_db(self):
        super()._migrate_db()

        if self.db_schema_version < 1:
            self._update_nonsingleton_to_schema(1, self.__update_schema_version_1)

    def __update_schema_version_1(self, specific_execution_db: Database):
        # Change execution to be a single instance, so we rename all collections over
        admin_db = self.db.client['admin']
        for collection_name in specific_execution_db.list_collection_names():
            admin_db.command({
                'renameCollection': f'{specific_execution_db.name}.{collection_name}',
                'to': f'{GENERAL_INFO_PLUGIN_NAME}.{collection_name}'
            })


@pytest.fixture(scope="module")
def general_info_fixture(request):
    service = GeneralInfoService()
    initialize_fixture(request, service)
    return service
