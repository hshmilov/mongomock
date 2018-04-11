import pytest
import json
from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture
from services.triggerable_service import TriggerableService


class DeviceControlService(PluginService, TriggerableService):
    def __init__(self):
        super().__init__('device-control')

    def run_action(self, payload, *vargs, **kwargs):
        result = self.post('test_run_action', data=json.dumps(payload), *vargs, **kwargs)
        assert result.status_code == 200
        return result


@pytest.fixture(scope="module")
def device_control_fixture(request):
    service = DeviceControlService()
    initialize_fixture(request, service)
    return service
