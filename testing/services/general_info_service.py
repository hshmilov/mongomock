import pytest

from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture
from services.triggerable_service import TriggerableService


class GeneralInfoService(PluginService, TriggerableService):
    def __init__(self):
        super().__init__('general-info')


@pytest.fixture(scope="module")
def general_info_fixture(request):
    service = GeneralInfoService()
    initialize_fixture(request, service)
    return service
