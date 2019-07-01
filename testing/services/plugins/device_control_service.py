import pytest
import json

from axonius.consts.plugin_consts import DEVICE_CONTROL_PLUGIN_NAME
from pymongo.database import Database

from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture
from services.triggerable_service import TriggerableService
from services.updatable_service import UpdatablePluginMixin


class DeviceControlService(PluginService, TriggerableService, UpdatablePluginMixin):
    def __init__(self):
        super().__init__('device-control')

    def run_action(self, payload, *vargs, **kwargs):
        result = self.post('test_run_action', data=json.dumps(payload), *vargs, **kwargs)
        assert result.status_code == 200
        return result

    def _migrate_db(self):
        super()._migrate_db()

        if self.db_schema_version < 1:
            self._update_nonsingleton_to_schema(1, self.__update_schema_version_1)

    def __update_schema_version_1(self, specific_device_control_db: Database):
        # Change execution to be a single instance, so we rename all collections over
        admin_db = self.db.client['admin']
        for collection_name in specific_device_control_db.list_collection_names():
            admin_db.command({
                'renameCollection': f'{specific_device_control_db.name}.{collection_name}',
                'to': f'{DEVICE_CONTROL_PLUGIN_NAME}.{collection_name}'
            })


@pytest.fixture(scope="module")
def device_control_fixture(request):
    service = DeviceControlService()
    initialize_fixture(request, service)
    return service
