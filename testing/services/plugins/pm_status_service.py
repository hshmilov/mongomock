import pytest

from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture
from services.triggerable_service import TriggerableService


class PmStatusService(PluginService, TriggerableService):
    def __init__(self):
        super().__init__('pm-status')


@pytest.fixture(scope="module")
def pm_status_fixture(request):
    service = PmStatusService()
    initialize_fixture(request, service)
    return service
